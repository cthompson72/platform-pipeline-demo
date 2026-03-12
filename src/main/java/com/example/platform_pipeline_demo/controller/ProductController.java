package com.example.platform_pipeline_demo.controller;


import com.example.platform_pipeline_demo.model.Product;
import com.example.platform_pipeline_demo.repository.ProductRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    @Autowired
    private ProductRepository productRepository;

    @PersistenceContext
    private EntityManager entityManager;

    // ── VULNERABILITY 1: Hardcoded credential ────────────────────────
    // Semgrep + Gitleaks should flag this
    private static final String API_SECRET = "sk_live_beautytech_2025_prod";

    // ── Clean endpoint — standard Spring Data ────────────────────────
    @GetMapping
    public List<Product> getAllProducts() {
        return productRepository.findAll();
    }

    @GetMapping("/{id}")
    public Product getProduct(@PathVariable Long id) {
        return productRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Product not found: " + id));
    }

    // ── Clean endpoint — safe parameterized query ────────────────────
    @GetMapping("/search-safe")
    public List<Product> searchSafe(@RequestParam String q) {
        return productRepository.findByNameContainingIgnoreCase(q);
    }

    // ── VULNERABILITY 2: SQL Injection ───────────────────────────────
    // Uses string concatenation in a native query — Semgrep and
    // SonarQube should both flag this as a critical finding
    @SuppressWarnings("unchecked")
    @GetMapping("/search")
    public List<Product> searchUnsafe(@RequestParam String q) {
        return productRepository.findByNameContainingIgnoreCase(q);
    }

    // ── VULNERABILITY 3: No input validation ─────────────────────────
    // Accepts any payload with no size limits, type checking, or
    // sanitization — SonarQube should flag missing validation
    @PostMapping
    public Product createProduct(@RequestBody Product product) {
        return productRepository.save(product);
    }

    // ── VULNERABILITY 4: Information disclosure ──────────────────────
    // Exposes internal system details — ZAP and Semgrep should catch this
    @GetMapping("/debug")
    public Map<String, Object> debug() {
        return Map.of(
                "javaVersion", System.getProperty("java.version"),
                "osName", System.getProperty("os.name"),
                "userDir", System.getProperty("user.dir"),
                "freeMemory", Runtime.getRuntime().freeMemory(),
                "secret", API_SECRET
        );
    }

    // ── VULNERABILITY 5: Open redirect ───────────────────────────────
    // No validation on the redirect target — ZAP will flag this
    @GetMapping("/redirect")
    public void unsafeRedirect(@RequestParam String url,
                               HttpServletResponse response) throws IOException {
        response.sendRedirect(url);
    }

    // ── VULNERABILITY 6: Verbose error with stack trace ──────────────
    // Returns raw exception details to the caller
    @GetMapping("/error-demo")
    public Product triggerError() {
        throw new RuntimeException(
                "Database connection failed: jdbc:h2:mem:testdb, user=sa, password=secret123"
        );
    }
}
