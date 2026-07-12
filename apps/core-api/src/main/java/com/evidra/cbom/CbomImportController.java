package com.evidra.cbom;

import java.io.IOException;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/cboms")
public class CbomImportController {

    private final CbomImportService cbomImportService;
    private final CbomReportGenerator cbomReportGenerator;

    public CbomImportController(CbomImportService cbomImportService, CbomReportGenerator cbomReportGenerator) {
        this.cbomImportService = cbomImportService;
        this.cbomReportGenerator = cbomReportGenerator;
    }

    @PostMapping(path = "/import", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public CbomImportResponse importCbom(@RequestParam("file") MultipartFile file) throws IOException {
        return cbomImportService.importCbom(file);
    }

    @PostMapping(path = "/report", consumes = MediaType.MULTIPART_FORM_DATA_VALUE, produces = "text/markdown")
    public ResponseEntity<String> report(@RequestParam("file") MultipartFile file) throws IOException {
        CbomImportResponse importResponse = cbomImportService.importCbom(file);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("text/markdown"))
                .body(cbomReportGenerator.generate(importResponse));
    }
}
