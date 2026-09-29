package com.example.shortener.service;

public class LinkConflictException extends RuntimeException {
    public LinkConflictException(String message) { super(message); }
}
