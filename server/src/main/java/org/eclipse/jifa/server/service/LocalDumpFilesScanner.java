/********************************************************************************
 * Copyright (c) 2023 Contributors to the Eclipse Foundation
 *
 * See the NOTICE file(s) distributed with this work for additional
 * information regarding copyright ownership.
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0
 *
 * SPDX-License-Identifier: EPL-2.0
 ********************************************************************************/
package org.eclipse.jifa.server.service;

import lombok.extern.slf4j.Slf4j;
import org.eclipse.jifa.server.ConfigurationAccessor;
import org.eclipse.jifa.server.enums.FileType;
import org.eclipse.jifa.server.enums.Role;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;
import java.util.stream.Stream;

@Service
@Slf4j
public class LocalDumpFilesScanner extends ConfigurationAccessor {

    private final AnalysisApiService analysisApiService;
    private final FileService fileService;
    private volatile boolean isScanning = false;

    public LocalDumpFilesScanner(AnalysisApiService analysisApiService, FileService fileService) {
        this.analysisApiService = analysisApiService;
        this.fileService = fileService;
    }

    @Scheduled(fixedDelayString = "${jifa.local-dump-files-scan-interval:300}", timeUnit = TimeUnit.SECONDS, initialDelay = 10)
    public void scheduledScan() {
        if (config.getRole() != Role.STANDALONE_WORKER) {
            return;
        }

        // Skip periodic scan if FileWatcher is enabled
        if (config.isUseFileWatcher()) {
            return;
        }

        Path dumpFilesDir = config.getLocalDumpFilesDirectory();
        if (dumpFilesDir == null || config.getLocalDumpFilesScanInterval() <= 0) {
            return;
        }

        scanDirectory(dumpFilesDir);
    }

    public void scanDirectory(Path dumpFilesDir) {
        if (isScanning) {
            log.debug("Scan already in progress, skipping");
            return;
        }

        if (!Files.exists(dumpFilesDir) || !Files.isDirectory(dumpFilesDir)) {
            log.warn("Local dump files directory does not exist or is not a directory: {}", dumpFilesDir);
            return;
        }

        isScanning = true;
        try {
            log.info("Scanning local dump files directory: {}", dumpFilesDir);
            try (Stream<Path> files = Files.walk(dumpFilesDir, 1)) {
                files.filter(Files::isRegularFile)
                     .filter(this::isSupportedFile)
                     .forEach(this::handleInputFile);
            }
        } catch (IOException e) {
            log.error("Failed to scan local dump files directory '{}': {}", dumpFilesDir, e.getMessage());
        } finally {
            isScanning = false;
        }
    }

    private boolean isSupportedFile(Path path) {
        String name = path.getFileName().toString().toLowerCase();
        return name.endsWith(".hprof") ||
               name.endsWith(".hprof.gz") ||
               name.endsWith(".bin") ||
               name.endsWith(".log") ||
               name.endsWith(".txt");
    }

    private void handleInputFile(Path path) {
        try {
            String fileName = path.getFileName().toString();

            // Check if already loaded
            FileType estimatedType = estimateFileType(fileName);
            if (estimatedType != null && fileService.isFileAlreadyLoaded(fileName, estimatedType)) {
                log.debug("File already loaded, skipping: {}", fileName);
                return;
            }

            // Wait for file to become stable (not being written to)
            // This prevents scanning files that are still being downloaded
            waitForFileStable(path);

            // MAT natively supports .gz files, no need to decompress
            FileType type = analysisApiService.deduceFileType(path);
            if (type != null) {
                boolean useSymlink = config.isUseSymbolicLinkForLocalFiles();
                String uniqueName = fileService.handleLocalFileRequest(type, path, useSymlink);
                log.info("{}: http://{}:{}/{}/{}",
                         fileName,
                         "localhost",
                         config.getPort(),
                         type.getAnalysisUrlPath(),
                         uniqueName);
            } else {
                log.warn("Unable to deduce file type for: {}", path);
            }
        } catch (IOException e) {
            log.error("Failed to handle input file '{}': {}", path, e.getMessage(), e);
        }
    }

    /**
     * Wait for file to become stable (not being written to).
     * This ensures that files being downloaded are fully written before processing.
     */
    private void waitForFileStable(Path filePath) {
        try {
            long lastSize = -1;
            int stableCount = 0;
            int maxAttempts = 120; // 120 * 500ms = 60 seconds max wait

            for (int i = 0; i < maxAttempts; i++) {
                if (!Files.exists(filePath)) {
                    return;
                }

                long currentSize = Files.size(filePath);
                if (currentSize == lastSize) {
                    stableCount++;
                    if (stableCount >= 2) {
                        // File size hasn't changed for 2 consecutive checks
                        return;
                    }
                } else {
                    stableCount = 0;
                }

                lastSize = currentSize;
                Thread.sleep(500); // Wait 500ms between checks
            }

            log.warn("File may still be being written after {} seconds: {}", maxAttempts * 0.5, filePath);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (IOException e) {
            log.warn("Failed to check file size: {}", e.getMessage());
        }
    }

    /**
     * Handle a single file - exposed for FileWatcher to use
     */
    public void handleSingleFile(Path path) {
        if (!Files.isRegularFile(path) || !isSupportedFile(path)) {
            return;
        }
        handleInputFile(path);
    }

    private FileType estimateFileType(String fileName) {
        String lowerName = fileName.toLowerCase();
        if (lowerName.endsWith(".hprof") || lowerName.endsWith(".hprof.gz")) {
            return FileType.HEAP_DUMP;
        } else if (lowerName.endsWith(".log")) {
            return FileType.GC_LOG;
        } else if (lowerName.endsWith(".txt")) {
            return FileType.THREAD_DUMP;
        }
        return null;
    }
}
