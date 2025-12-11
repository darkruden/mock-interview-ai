// e2e/playwright.config.js
import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';

// Carrega variáveis de ambiente (para login)
dotenv.config();

export default defineConfig({
    testDir: './tests',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: 'html',

    use: {
        // URL base do seu frontend local ou produção
        baseURL: process.env.BASE_URL || 'http://localhost:5173',

        // Coleta trace quando falha (muito útil para debug)
        trace: 'on-first-retry',
        // Grava vídeo apenas quando falha
        video: 'retain-on-failure',
        // Tira print quando falha
        screenshot: 'only-on-failure',
    },

    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
});