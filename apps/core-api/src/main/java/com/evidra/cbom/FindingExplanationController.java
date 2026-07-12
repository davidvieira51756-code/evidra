package com.evidra.cbom;

import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/findings")
@CrossOrigin(origins = "http://localhost:3000")
public class FindingExplanationController {

    private final FindingExplanationService findingExplanationService;

    public FindingExplanationController(FindingExplanationService findingExplanationService) {
        this.findingExplanationService = findingExplanationService;
    }

    @PostMapping("/explain")
    public FindingExplanationResponse explain(@RequestBody FindingExplanationRequest request) {
        return findingExplanationService.explain(request);
    }
}
