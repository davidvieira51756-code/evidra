package com.evidra.cbom;

import static org.hamcrest.Matchers.is;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.charset.StandardCharsets;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class CbomImportControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void importsValidCycloneDxCbom() throws Exception {
        MockMultipartFile file = jsonFile("""
                {
                  "bomFormat": "CycloneDX",
                  "specVersion": "1.6",
                  "serialNumber": "urn:uuid:11111111-1111-1111-1111-111111111111",
                  "version": 1,
                  "components": [
                    { "type": "library", "name": "bcprov-jdk18on", "version": "1.78" }
                  ]
                }
                """);

        mockMvc.perform(multipart("/api/cboms/import").file(file))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status", is("accepted")))
                .andExpect(jsonPath("$.bomFormat", is("CycloneDX")))
                .andExpect(jsonPath("$.specVersion", is("1.6")))
                .andExpect(jsonPath("$.serialNumber", is("urn:uuid:11111111-1111-1111-1111-111111111111")))
                .andExpect(jsonPath("$.version", is(1)))
                .andExpect(jsonPath("$.componentCount", is(1)));
    }

    @Test
    void rejectsEmptyFile() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "cbom.json",
                "application/json",
                new byte[0]);

        mockMvc.perform(multipart("/api/cboms/import").file(file))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code", is("INVALID_CBOM")))
                .andExpect(jsonPath("$.message", is("CBOM file is required.")));
    }

    @Test
    void rejectsInvalidJson() throws Exception {
        MockMultipartFile file = jsonFile("{ invalid json");

        mockMvc.perform(multipart("/api/cboms/import").file(file))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code", is("INVALID_CBOM")))
                .andExpect(jsonPath("$.message", is("CBOM file must be valid JSON.")));
    }

    @Test
    void rejectsJsonThatIsNotCycloneDx() throws Exception {
        MockMultipartFile file = jsonFile("""
                {
                  "bomFormat": "SPDX",
                  "specVersion": "2.3"
                }
                """);

        mockMvc.perform(multipart("/api/cboms/import").file(file))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code", is("INVALID_CBOM")))
                .andExpect(jsonPath("$.message", is("CBOM file must use CycloneDX bomFormat.")));
    }

    @Test
    void rejectsCycloneDxWithoutSpecVersion() throws Exception {
        MockMultipartFile file = jsonFile("""
                {
                  "bomFormat": "CycloneDX"
                }
                """);

        mockMvc.perform(multipart("/api/cboms/import").file(file))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code", is("INVALID_CBOM")))
                .andExpect(jsonPath("$.message", is("CBOM file must contain a non-empty specVersion field.")));
    }

    private MockMultipartFile jsonFile(String content) {
        return new MockMultipartFile(
                "file",
                "cbom.json",
                "application/json",
                content.getBytes(StandardCharsets.UTF_8));
    }
}
