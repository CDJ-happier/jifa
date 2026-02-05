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
import org.eclipse.jifa.server.enums.Role;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.io.IOException;
import java.nio.file.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * File watcher service that monitors the local dump files directory for new files.
 * Uses Java NIO WatchService for efficient file system monitoring instead of polling.
 */
@Service
@Slf4j
public class LocalDumpFilesWatcher extends ConfigurationAccessor {

    private final LocalDumpFilesScanner scanner;
    private WatchService watchService;
    private ExecutorService executorService;
    private volatile boolean running = false;

    public LocalDumpFilesWatcher(LocalDumpFilesScanner scanner) {
        this.scanner = scanner;
    }

    @PostConstruct
    public void start() {
        if (config.getRole() != Role.STANDALONE_WORKER) {
            return;
        }

        Path dumpFilesDir = config.getLocalDumpFilesDirectory();
        if (dumpFilesDir == null || !Files.exists(dumpFilesDir) || !Files.isDirectory(dumpFilesDir)) {
            log.info("Local dump files directory not configured or does not exist, file watcher disabled");
            return;
        }

        try {
            watchService = FileSystems.getDefault().newWatchService();

            // Register the directory for CREATE and MODIFY events
            dumpFilesDir.register(
                watchService,
                StandardWatchEventKinds.ENTRY_CREATE,
                StandardWatchEventKinds.ENTRY_MODIFY
            );

            running = true;
            executorService = Executors.newSingleThreadExecutor(r -> {
                Thread t = new Thread(r, "LocalDumpFilesWatcher");
                t.setDaemon(true);
                return t;
            });

            executorService.submit(this::watchLoop);

            log.info("Started file watcher for directory: {}", dumpFilesDir);

            // Do initial scan
            scanner.scanDirectory(dumpFilesDir);

        } catch (IOException e) {
            log.error("Failed to start file watcher: {}", e.getMessage(), e);
        }
    }

    private void watchLoop() {
        Path dumpFilesDir = config.getLocalDumpFilesDirectory();
        log.debug("File watcher loop started for: {}", dumpFilesDir);

        while (running) {
            try {
                // Wait for events (blocking call)
                WatchKey key = watchService.poll(1, TimeUnit.SECONDS);
                if (key == null) {
                    continue;
                }

                for (WatchEvent<?> event : key.pollEvents()) {
                    WatchEvent.Kind<?> kind = event.kind();

                    // Handle overflow
                    if (kind == StandardWatchEventKinds.OVERFLOW) {
                        log.warn("Watch service overflow, performing full scan");
                        scanner.scanDirectory(dumpFilesDir);
                        continue;
                    }

                    @SuppressWarnings("unchecked")
                    WatchEvent<Path> pathEvent = (WatchEvent<Path>) event;
                    Path fileName = pathEvent.context();
                    Path filePath = dumpFilesDir.resolve(fileName);

                    // Only process regular files
                    if (!Files.isRegularFile(filePath)) {
                        continue;
                    }

                    // Check if it's a supported file type
                    String name = fileName.toString().toLowerCase();
                    boolean isSupported = name.endsWith(".hprof") ||
                                        name.endsWith(".hprof.gz") ||
                                        name.endsWith(".bin") ||
                                        name.endsWith(".log") ||
                                        name.endsWith(".txt");

                    if (!isSupported) {
                        continue;
                    }

                    // For CREATE events, process immediately
                    if (kind == StandardWatchEventKinds.ENTRY_CREATE) {
                        log.info("Detected new file: {}", fileName);

                        // Wait a bit to ensure file is completely written
                        waitForFileStable(filePath);

                        // Process the new file
                        scanner.handleSingleFile(filePath);
                    }
                    // For MODIFY events, we can choose to ignore or handle
                    else if (kind == StandardWatchEventKinds.ENTRY_MODIFY) {
                        log.debug("File modified: {} (ignoring)", fileName);
                        // Typically we don't want to reprocess modified files
                    }
                }

                // Reset the key
                boolean valid = key.reset();
                if (!valid) {
                    log.warn("Watch key no longer valid, stopping watcher");
                    break;
                }

            } catch (InterruptedException e) {
                log.info("File watcher interrupted");
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                log.error("Error in file watcher loop: {}", e.getMessage(), e);
            }
        }

        log.info("File watcher loop stopped");
    }

    /**
     * Wait for file to become stable (not being written to)
     */
    private void waitForFileStable(Path filePath) {
        try {
            long lastSize = -1;
            int stableCount = 0;
            int maxAttempts = 10;

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

    @PreDestroy
    public void stop() {
        running = false;

        if (watchService != null) {
            try {
                watchService.close();
            } catch (IOException e) {
                log.error("Error closing watch service: {}", e.getMessage());
            }
        }

        if (executorService != null) {
            executorService.shutdown();
            try {
                if (!executorService.awaitTermination(5, TimeUnit.SECONDS)) {
                    executorService.shutdownNow();
                }
            } catch (InterruptedException e) {
                executorService.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }

        log.info("File watcher stopped");
    }
}
