package com.evidra.cbom;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class FindingExplanationService {

    private final RestClient restClient;

    public FindingExplanationService(
            RestClient.Builder restClientBuilder,
            @Value("${evidra.ai-service.base-url:http://localhost:8000}") String aiServiceBaseUrl) {
        this.restClient = restClientBuilder
                .baseUrl(aiServiceBaseUrl)
                .build();
    }

    public FindingExplanationResponse explain(FindingExplanationRequest request) {
        FindingExplanationResponse response = restClient.post()
                .uri("/findings/explain")
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(FindingExplanationResponse.class);

        if (response == null) {
            throw new IllegalStateException("AI service returned an empty explanation response.");
        }

        return response;
    }
}
