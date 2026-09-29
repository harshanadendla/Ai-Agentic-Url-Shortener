package com.example.shortener.service;

public class LinkNotFoundException extends RuntimeException {
    public LinkNotFoundException(String message) { super(message); }
}
