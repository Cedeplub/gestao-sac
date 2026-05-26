// Inicializar Lucide após HTMX swap e no carregamento
document.addEventListener('htmx:afterSwap', () => {
    if (typeof lucide !== 'undefined') lucide.createIcons();
});
document.addEventListener('DOMContentLoaded', () => {
    if (typeof lucide !== 'undefined') lucide.createIcons();
});

// Redirecionar para login em caso de 401
document.body.addEventListener('htmx:responseError', function (evt) {
    if (evt.detail.xhr.status === 401) {
        window.location.href = '/login';
    }
});

// Toast global: exibir via evento HTMX
document.body.addEventListener('htmx:afterRequest', function (evt) {
    const header = evt.detail.xhr.getResponseHeader('HX-Trigger');
    if (header) {
        try {
            const triggers = JSON.parse(header);
            if (triggers.showToast) {
                showToast(triggers.showToast.message, triggers.showToast.type || 'success');
            }
        } catch (e) { /* não é JSON */ }
    }
});

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        warning: 'bg-yellow-500',
    };

    const div = document.createElement('div');
    div.className = `${colors[type] || colors.success} text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 transition-all duration-300`;
    div.innerHTML = `<span>${message}</span>`;
    container.appendChild(div);

    setTimeout(() => {
        div.style.opacity = '0';
        setTimeout(() => div.remove(), 300);
    }, 4000);
}
