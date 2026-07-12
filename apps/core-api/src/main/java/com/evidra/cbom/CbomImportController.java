package com.evidra.cbom;

import java.io.IOException;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/cboms")
public class CbomImportController {

    private final CbomImportService cbomImportService;

    public CbomImportController(CbomImportService cbomImportService) {
        this.cbomImportService = cbomImportService;
    }

    @PostMapping(path = "/import", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public CbomImportResponse importCbom(@RequestParam("file") MultipartFile file) throws IOException {
        return cbomImportService.importCbom(file);
    }
}
