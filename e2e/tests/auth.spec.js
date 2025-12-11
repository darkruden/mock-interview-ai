import { test, expect } from '@playwright/test';

test.describe('Autenticação e Acesso Inicial', () => {

    test('deve redirecionar para a tela de login ao abrir o app', async ({ page }) => {
        await page.goto('/');

        // 1. Espera o formulário de login aparecer (Container principal)
        // O Amplify geralmente coloca um fieldset ou form
        await expect(page.locator('form')).toBeVisible();

        // 2. Verifica se o botão de "Sign in" ou "Entrar" está visível
        // Usamos Regex (/sign in/i) para pegar qualquer variação de maiúscula/minúscula
        await expect(page.getByRole('button', { name: /sign in|entrar/i })).toBeVisible();
    });

    test('deve conseguir fazer login e ver a tela "MOCK.LIVE"', async ({ page }) => {
        // Pula se não houver credenciais
        if (!process.env.E2E_USER_EMAIL || !process.env.E2E_USER_PASSWORD) {
            test.skip('Credenciais E2E não configuradas no .env');
            return;
        }

        await page.goto('/');

        // --- ESTRATÉGIA DE LOGIN ROBUSTA ---

        // 1. Preencher Email
        // Tentamos encontrar pelo Label "Email" ou "Enter your email" genericamente
        // Ou pelo input com name="username" (padrão do Cognito)
        const emailInput = page.locator('input[name="username"]');
        await emailInput.fill(process.env.E2E_USER_EMAIL);

        // 2. Preencher Senha
        const passwordInput = page.locator('input[name="password"]');
        await passwordInput.fill(process.env.E2E_USER_PASSWORD);

        // 3. Clicar em Login
        await page.getByRole('button', { name: /sign in|entrar/i }).click();

        // --- VALIDAÇÃO ---

        // 4. Aguarda o título principal. Aumentamos o timeout para 20s pois o login pode ser lento.
        await expect(page.getByText('MOCK.LIVE')).toBeVisible({ timeout: 20000 });

        // 5. Verifica estado inicial da aplicação
        await expect(page.getByText(/AGUARDANDO CONEXÃO|SISTEMA ONLINE/i)).toBeVisible();
    });
});