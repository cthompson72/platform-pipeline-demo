package com.example.platform_pipeline_demo.controller;

import com.example.platform_pipeline_demo.model.Product;
import com.example.platform_pipeline_demo.repository.ProductRepository;
import tools.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class ProductControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void shouldReturnAllProducts() throws Exception {
        mockMvc.perform(get("/api/products"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThanOrEqualTo(10))))
                .andExpect(jsonPath("$[0].name").exists())
                .andExpect(jsonPath("$[0].brand").exists());
    }

    @Test
    void shouldReturnProductById() throws Exception {
        mockMvc.perform(get("/api/products/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name", is("Revitalift Serum")))
                .andExpect(jsonPath("$.brand", is("L'Oreal Paris")));
    }

    @Test
    void shouldReturn404ForMissingProduct() throws Exception {
        mockMvc.perform(get("/api/products/9999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void shouldSearchProductsSafely() throws Exception {
        mockMvc.perform(get("/api/products/search-safe")
                        .param("q", "Serum"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThanOrEqualTo(1))))
                .andExpect(jsonPath("$[0].name", containsString("Serum")));
    }

    @Test
    void shouldSearchProducts() throws Exception {
        mockMvc.perform(get("/api/products/search")
                        .param("q", "Mascara"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThanOrEqualTo(1))));
    }

    @Test
    void shouldSearchReturnEmptyList() throws Exception {
        mockMvc.perform(get("/api/products/search")
                        .param("q", "nonexistent"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(0)));
    }

    @Test
    void shouldCreateProduct() throws Exception {
        Product newProduct = new Product("Test Lipstick", "L'Oreal Paris", "makeup", new BigDecimal("14.99"));

        mockMvc.perform(post("/api/products")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(newProduct)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.name", is("Test Lipstick")));
    }

    @Test
    void shouldRejectProductWithMissingName() throws Exception {
        String body = """
                {"brand":"Test","price":10.00,"category":"skincare"}
                """;
        mockMvc.perform(post("/api/products")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error", is("Validation Failed")))
                .andExpect(jsonPath("$.messages", hasSize(greaterThanOrEqualTo(1))));
    }

    @Test
    void shouldReturnDetailedHealth() throws Exception {
        mockMvc.perform(get("/api/products/health/detailed"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status", is("UP")))
                .andExpect(jsonPath("$.memory").exists())
                .andExpect(jsonPath("$.uptime").exists())
                .andExpect(jsonPath("$.productCount").exists());
    }

    @Test
    void shouldReturnDebugInfo() throws Exception {
        mockMvc.perform(get("/api/products/debug"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.javaVersion").exists());
    }

    @Test
    void shouldReturnHealthCheck() throws Exception {
        mockMvc.perform(get("/actuator/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status", is("UP")));
    }
}
