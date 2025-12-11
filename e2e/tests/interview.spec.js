import { test, expect } from '@playwright/test';

test('deve exibir interface de conexão e permitir clique', async ({ page }) => {
    if (process.env.E2E_USER_EMAIL) {
        await page.goto('/');

        // --- LOGIN ROBUSTO (Igual ao auth.spec.js) ---
        await page.locator('input[name="username"]').fill(process.env.E2E_USER_EMAIL);
        await page.locator('input[name="password"]').fill(process.env.E2E_USER_PASSWORD);
        await page.getByRole('button', { name: /sign in|entrar/i }).click();

        // Espera o login completar
        await expect(page.getByText('MOCK.LIVE')).toBeVisible({ timeout: 20000 });
    } else {
        test.skip('Requer login para testar a entrevista');
    }

    // 1. Verifica botão de iniciar (Telefone)
    // O seletor 'button' dentro do main container.
    // Como seu botão tem classes específicas do Tailwind, podemos tentar algo genérico ou específico
    // Vamos procurar pelo texto "CLIQUE PARA INICIAR" que está logo abaixo do botão
    await expect(page.getByText('CLIQUE PARA INICIAR')).toBeVisible();

    // 2. Encontra o botão visualmente (O círculo grande) e clica
    // Uma estratégia segura é pegar o botão que está próximo ao texto
    const startButton = page.getByRole('button').first(); // Geralmente é o primeiro botão grande na tela logada
    await startButton.click();

    // 3. Verifica mudança de estado visual
    // Ao clicar, o texto "CLIQUE PARA INICIAR" deve sumir ou o status deve mudar
    // Como não temos backend real rodando para o WebSocket, ele pode ir para "connecting" ou "error"
    // Vamos verificar se o texto de instrução sumiu, indicando interação
    await expect(page.getByText('CLIQUE PARA INICIAR')).not.toBeVisible();
});