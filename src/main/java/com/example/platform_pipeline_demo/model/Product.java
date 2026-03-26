package com.example.platform_pipeline_demo.model;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank(message = "name must not be blank")
    @Size(max = 100, message = "name must be at most 100 characters")
    private String name;

    @NotBlank(message = "brand must not be blank")
    private String brand;

    @Size(max = 500, message = "description must be at most 500 characters")
    private String description;

    @DecimalMin(value = "0.01", message = "price must be greater than 0")
    private BigDecimal price;

    @NotBlank(message = "category must not be blank")
    private String category;

    private boolean inStock = true;

    private LocalDateTime createdAt;

    public Product() {
        this.createdAt = LocalDateTime.now();
    }

    public Product(String name, String brand, String category, BigDecimal price) {
        this.name = name;
        this.brand = brand;
        this.category = category;
        this.price = price;
        this.inStock = true;
        this.createdAt = LocalDateTime.now();
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getBrand() { return brand; }
    public void setBrand(String brand) { this.brand = brand; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }

    public BigDecimal getPrice() { return price; }
    public void setPrice(BigDecimal price) { this.price = price; }

    public boolean isInStock() { return inStock; }
    public void setInStock(boolean inStock) { this.inStock = inStock; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
