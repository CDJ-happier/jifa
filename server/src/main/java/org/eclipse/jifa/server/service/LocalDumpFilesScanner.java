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

            // Skip files with size 0 - they are likely still being downloaded
            try {
                long fileSize = Files.size(path);
                if (fileSize == 0) {
                    log.warn("File {} has size 0, skipping (likely still being downloaded)", fileName);
                    return;
                }
            } catch (IOException e) {
                log.warn("Cannot read file size for {}, skipping", fileName);
                return;
            }

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
     * Uses longer intervals and more attempts to handle very large file downloads
     * (e.g. 80GB+ hprof files that may take hours to download).
     *
     * Strategy:
     * - Check every 10 seconds
     * - Require 3 consecutive stable checks (30 seconds of no size change)
     * - Maximum wait time: 6 hours (2160 attempts × 10 seconds)
     */
    private void waitForFileStable(Path filePath) {
        try {
            long lastSize = -1;
            int stableCount = 0;
            // Check every 10 seconds, up to 2160 times = 6 hours max wait
            // This accommodates very large file downloads (e.g. 80GB+ hprof)
            int checkIntervalMs = 10_000;
            int maxAttempts = 2160;
            int requiredStableChecks = 3; // Need 3 consecutive stable checks (30 seconds stable)

            for (int i = 0; i < maxAttempts; i++) {
                if (!Files.exists(filePath)) {
                    return;
                }

                long currentSize = Files.size(filePath);

                // File size is 0, likely just created and not yet written to
                if (currentSize == 0 && i < maxAttempts - 1) {
                    lastSize = 0;
                    stableCount = 0;
                    Thread.sleep(checkIntervalMs);
                    continue;
                }

                if (currentSize == lastSize && currentSize > 0) {
                    stableCount++;
                    if (stableCount >= requiredStableChecks) {
                        log.info("File {} stabilized at size {} bytes ({} MB) after ~{} seconds",
                                 filePath.getFileName(), currentSize, currentSize / (1024 * 1024),
                                 (long) i * checkIntervalMs / 1000);
                        return;
                    }
                } else {
                    stableCount = 0;
                }

                lastSize = currentSize;
                Thread.sleep(checkIntervalMs);

                // Periodic progress logging (every ~5 minutes)
                if (i > 0 && i % 30 == 0) {
                    log.info("Still waiting for file {} to stabilize: current size {} bytes ({} MB), " +
                             "elapsed ~{} minutes",
                             filePath.getFileName(), currentSize, currentSize / (1024 * 1024),
                             (long) i * checkIntervalMs / 60000);
                }
            }

            log.warn("File {} may still be being written after {} hours (current size: {} bytes)",
                     filePath.getFileName(), (long) maxAttempts * checkIntervalMs / 3600000, lastSize);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (IOException e) {
            log.warn("Failed to check file size for {}: {}", filePath, e.getMessage());
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
