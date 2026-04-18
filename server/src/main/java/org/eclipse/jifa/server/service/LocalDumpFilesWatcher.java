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
import java.util.Set;
import java.util.concurrent.*;

/**
 * File watcher service that monitors the local dump files directory for new files.
 * Uses Java NIO WatchService for efficient file system monitoring instead of polling.
 *
 * Architecture:
 * - A single daemon thread runs the watchLoop, consuming WatchService events.
 * - Each newly detected file is handed off to a thread pool for async stability checking,
 *   so the watch loop is NEVER blocked by long-running waitForFileStable calls.
 * - A ConcurrentSet tracks files currently being processed to avoid duplicate handling.
 */
@Service
@Slf4j
public class LocalDumpFilesWatcher extends ConfigurationAccessor {

    private final LocalDumpFilesScanner scanner;
    private WatchService watchService;
    private ExecutorService watchLoopExecutor;
    private ExecutorService fileProcessingPool;
    private volatile boolean running = false;

    /**
     * Track files currently being processed (waiting for stable / registering).
     * Prevents duplicate processing if multiple events fire for the same file.
     */
    private final Set<Path> filesInProgress = ConcurrentHashMap.newKeySet();

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

            // Single thread for the watch loop (event consumer)
            watchLoopExecutor = Executors.newSingleThreadExecutor(r -> {
                Thread t = new Thread(r, "LocalDumpFilesWatcher");
                t.setDaemon(true);
                return t;
            });

            // Thread pool for async file stability checking and processing.
            // Use a cached pool so multiple large files can be waited on concurrently.
            fileProcessingPool = Executors.newCachedThreadPool(r -> {
                Thread t = new Thread(r, "DumpFileProcessor");
                t.setDaemon(true);
                return t;
            });

            watchLoopExecutor.submit(this::watchLoop);

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
                // Wait for events (blocking call with timeout so we can check 'running' flag)
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

                    // For CREATE events, submit async processing (don't block watch loop!)
                    if (kind == StandardWatchEventKinds.ENTRY_CREATE) {
                        if (filesInProgress.contains(filePath)) {
                            log.debug("File {} is already being processed, ignoring duplicate CREATE event", fileName);
                            continue;
                        }

                        log.info("Detected new file: {}, submitting for async processing", fileName);
                        filesInProgress.add(filePath);

                        fileProcessingPool.submit(() -> processNewFileAsync(filePath));
                    }
                    // For MODIFY events, we can choose to ignore or handle
                    else if (kind == StandardWatchEventKinds.ENTRY_MODIFY) {
                        log.debug("File modified: {} (ignoring)", fileName);
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
            } catch (ClosedWatchServiceException e) {
                log.info("Watch service closed, stopping watcher");
                break;
            } catch (Exception e) {
                log.error("Error in file watcher loop: {}", e.getMessage(), e);
            }
        }

        log.info("File watcher loop stopped");
    }

    /**
     * Async processing of a new file: wait for it to stabilize, then hand off to scanner.
     * Runs in the fileProcessingPool, does NOT block the watch loop.
     */
    private void processNewFileAsync(Path filePath) {
        try {
            Path fileName = filePath.getFileName();
            log.info("Starting stability check for file: {}", fileName);

            boolean stable = waitForFileStable(filePath);
            if (!stable) {
                log.warn("File {} did not stabilize within timeout (6 hours). " +
                         "It will be picked up on next application restart or manual scan.", fileName);
                return;
            }

            // Process the new file
            scanner.handleSingleFile(filePath);

        } catch (Exception e) {
            log.error("Error processing new file {}: {}", filePath, e.getMessage(), e);
        } finally {
            filesInProgress.remove(filePath);
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
     * - Files with size 0 are considered still being initialized
     *
     * @return true if the file is stable, false if still being written after timeout
     */
    private boolean waitForFileStable(Path filePath) {
        try {
            long lastSize = -1;
            int stableCount = 0;
            // Check every 10 seconds, up to 2160 times = 6 hours max wait
            // This accommodates very large file downloads (e.g. 80GB+ hprof)
            int checkIntervalMs = 10_000;
            int maxAttempts = 2160;
            int requiredStableChecks = 3; // Need 3 consecutive stable checks (30 seconds stable)

            for (int i = 0; i < maxAttempts; i++) {
                if (!running) {
                    log.info("Watcher shutting down, aborting stability check for {}", filePath.getFileName());
                    return false;
                }

                if (!Files.exists(filePath)) {
                    log.warn("File {} disappeared during stability check", filePath.getFileName());
                    return false;
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
                        return true;
                    }
                } else {
                    if (stableCount > 0) {
                        log.debug("File {} size changed from {} to {}, resetting stable count",
                                  filePath.getFileName(), lastSize, currentSize);
                    }
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
            return false;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        } catch (IOException e) {
            log.warn("Failed to check file size for {}: {}", filePath, e.getMessage());
            return false;
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

        if (watchLoopExecutor != null) {
            watchLoopExecutor.shutdown();
            try {
                if (!watchLoopExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                    watchLoopExecutor.shutdownNow();
                }
            } catch (InterruptedException e) {
                watchLoopExecutor.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }

        if (fileProcessingPool != null) {
            fileProcessingPool.shutdown();
            try {
                // Give processing threads a bit more time to finish
                if (!fileProcessingPool.awaitTermination(10, TimeUnit.SECONDS)) {
                    fileProcessingPool.shutdownNow();
                }
            } catch (InterruptedException e) {
                fileProcessingPool.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }

        log.info("File watcher stopped");
    }
}
