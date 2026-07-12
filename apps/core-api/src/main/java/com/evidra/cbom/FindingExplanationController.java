package com.evidra.cbom;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

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
        if (request == null || request.finding() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Finding is required.");
        }

        return findingExplanationService.explain(request);
    }
}
