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
package org.eclipse.jifa.server;

import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.SystemUtils;
import org.eclipse.jifa.server.enums.FileType;
import org.eclipse.jifa.server.enums.Role;
import org.eclipse.jifa.server.service.AnalysisApiService;
import org.eclipse.jifa.server.service.FileService;
import org.eclipse.jifa.server.service.LocalDumpFilesScanner;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.file.Path;

@Component
@Slf4j
class ReadyListener extends ConfigurationAccessor {

    private final AnalysisApiService analysisApiService;

    private final FileService fileService;

    private final LocalDumpFilesScanner localDumpFilesScanner;

    ReadyListener(AnalysisApiService analysisApiService, FileService fileService, LocalDumpFilesScanner localDumpFilesScanner) {
        this.analysisApiService = analysisApiService;
        this.fileService = fileService;
        this.localDumpFilesScanner = localDumpFilesScanner;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void fireReadyEvent() {
        Role role = config.getRole();
        if (role == Role.MASTER || role == Role.STANDALONE_WORKER) {
            //noinspection HttpUrlsUsage
            log.info("Jifa Server: http://{}:{}", "localhost", config.getPort());
        }

        if (config.getRole() == Role.STANDALONE_WORKER) {
            // Handle individual input files
            Path[] paths = config.getInputFiles();
            if (paths != null) {
                for (Path path : paths) {
                    handleInputFile(path);
                }
            }

            // Handle local dump files directory - use the scanner service
            Path dumpFilesDir = config.getLocalDumpFilesDirectory();
            if (dumpFilesDir != null) {
                localDumpFilesScanner.scanDirectory(dumpFilesDir);
            }

            if (config.isOpenBrowserWhenReady()) {
                openBrowser("http://localhost:" + config.getPort());
            }
        }
    }

    private void handleInputFile(Path path) {
        try {
            FileType type = analysisApiService.deduceFileType(path);
            if (type != null) {
                String uniqueName = fileService.handleLocalFileRequest(type, path);
                //noinspection HttpUrlsUsage
                log.info("{}: http://{}:{}/{}/{}",
                         path.getFileName(),
                         "localhost",
                         config.getPort(),
                         type.getAnalysisUrlPath(),
                         uniqueName);
            } else {
                log.warn("Unable to deduce file type for: {}", path);
            }
        } catch (IOException e) {
            log.error("Failed to handle input file '{}': {}", path, e.getMessage());
        }
    }

    private void openBrowser(String url) {
        ProcessBuilder pb;
        if (SystemUtils.IS_OS_WINDOWS) {
            pb = new ProcessBuilder("cmd", "/c", "start", url);
        } else if (SystemUtils.IS_OS_MAC) {
            pb = new ProcessBuilder("/usr/bin/open", url);
        } else {
            // Linux
            pb = new ProcessBuilder("xdg-open", url);
            pb.environment().put("DISPLAY", ":0");
        }
        pb.inheritIO();
        try {
            pb.start();
        } catch (IOException e) {
            log.error("Unable to open browser, please check!", e);
        }
    }
}
