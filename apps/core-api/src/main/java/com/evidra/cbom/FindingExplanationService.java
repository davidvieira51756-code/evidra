package com.evidra.cbom;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;

@Service
public class FindingExplanationService {

    private final HttpClient httpClient;
    private final URI explainUri;
    private final ObjectMapper objectMapper;

    public FindingExplanationService(
            ObjectMapper objectMapper,
            @Value("${evidra.ai-service.base-url:http://localhost:8000}") String aiServiceBaseUrl) {
        this.httpClient = HttpClient.newHttpClient();
        this.explainUri = URI.create(aiServiceBaseUrl + "/findings/explain");
        this.objectMapper = objectMapper;
    }

    public FindingExplanationResponse explain(FindingExplanationRequest request) {
        String requestBody = serializeRequest(request);

        HttpRequest httpRequest = HttpRequest.newBuilder(explainUri)
                .version(HttpClient.Version.HTTP_1_1)
                .header("Content-Type", MediaType.APPLICATION_JSON_VALUE)
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();

        try {
            HttpResponse<String> response = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new RestClientException(
                        "AI service returned " + response.statusCode() + ": " + response.body());
            }

            return objectMapper.readValue(response.body(), FindingExplanationResponse.class);
        } catch (IOException exception) {
            throw new RestClientException("AI service request failed.", exception);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new RestClientException("AI service request was interrupted.", exception);
        }
    }

    private String serializeRequest(FindingExplanationRequest request) {
        try {
            return objectMapper.writeValueAsString(request);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Failed to serialize finding explanation request.", exception);
        }
    }
}
