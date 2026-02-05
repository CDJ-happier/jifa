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

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;
import java.util.stream.Stream;
import java.util.zip.GZIPInputStream;

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
            boolean isGzipped = fileName.toLowerCase().endsWith(".gz");

            Path fileToAnalyze = path;
            Path tempUncompressedFile = null;

            // Handle .gz files for heap dumps only
            if (isGzipped && fileName.toLowerCase().contains(".hprof")) {
                String uncompressedName = fileName.substring(0, fileName.length() - 3); // Remove .gz

                // Check if already loaded (check uncompressed name)
                FileType estimatedType = FileType.HEAP_DUMP;
                if (fileService.isFileAlreadyLoaded(uncompressedName, estimatedType)) {
                    log.debug("File already loaded, skipping: {}", uncompressedName);
                    return;
                }

                log.info("Decompressing .gz file: {}", fileName);
                tempUncompressedFile = Files.createTempFile("jifa-decompress-", ".hprof");
                decompressGzFile(path, tempUncompressedFile);
                fileToAnalyze = tempUncompressedFile;

                // Update file name for later processing
                fileName = uncompressedName;
            } else {
                // Check if already loaded
                FileType estimatedType = estimateFileType(fileName);
                if (estimatedType != null && fileService.isFileAlreadyLoaded(fileName, estimatedType)) {
                    log.debug("File already loaded, skipping: {}", fileName);
                    return;
                }
            }

            FileType type = analysisApiService.deduceFileType(fileToAnalyze);
            if (type != null) {
                boolean useSymlink = config.isUseSymbolicLinkForLocalFiles() && !isGzipped;
                String uniqueName = fileService.handleLocalFileRequest(type, fileToAnalyze, useSymlink);
                log.info("{}: http://{}:{}/{}/{}",
                         fileName,
                         "localhost",
                         config.getPort(),
                         type.getAnalysisUrlPath(),
                         uniqueName);
            } else {
                log.warn("Unable to deduce file type for: {}", path);
            }

            // Clean up temp file if it was created
            if (tempUncompressedFile != null && !config.isUseSymbolicLinkForLocalFiles()) {
                try {
                    Files.deleteIfExists(tempUncompressedFile);
                } catch (IOException e) {
                    log.warn("Failed to delete temp file: {}", tempUncompressedFile, e);
                }
            }
        } catch (IOException e) {
            log.error("Failed to handle input file '{}': {}", path, e.getMessage(), e);
        }
    }

    private void decompressGzFile(Path gzFile, Path outputFile) throws IOException {
        try (GZIPInputStream gzis = new GZIPInputStream(
                new BufferedInputStream(new FileInputStream(gzFile.toFile())));
             BufferedOutputStream bos = new BufferedOutputStream(
                new FileOutputStream(outputFile.toFile()))) {

            byte[] buffer = new byte[8192];
            int len;
            while ((len = gzis.read(buffer)) > 0) {
                bos.write(buffer, 0, len);
            }
        }
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
