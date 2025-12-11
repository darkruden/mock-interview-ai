import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Limpa o DOM após cada teste para evitar "sujeira" de um teste afetar outro
afterEach(() => {
    cleanup();
});

// Mock do ResizeObserver (o Framer Motion precisa disso, mas o jsdom não tem)
global.ResizeObserver = class ResizeObserver {
    observe() { }
    unobserve() { }
    disconnect() { }
};