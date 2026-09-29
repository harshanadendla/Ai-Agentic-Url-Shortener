package com.example.shortener.service;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class UrlPolicyTest {
    private final UrlPolicy policy = new UrlPolicy();

    @Test
    void acceptsHttpAndHttps() {
        assertThat(policy.validateAndNormalize("https://example.com/a/../b")).isEqualTo("https://example.com/b");
    }

    @Test
    void rejectsNonWebSchemes() {
        assertThatThrownBy(() -> policy.validateAndNormalize("javascript:alert(1)"))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
