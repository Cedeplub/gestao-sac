// JS da página "Nova Ocorrência" — estado Alpine + handler de swap HTMX.
// Exposto em window para uso direto em x-data e como listener global.

window.ocorrenciaFormData = function () {
    return {
        produtos: [],
        selecionadosMap: {},
        motivo: '',
        causa: '',
        notaOk: false,
        arquivos: [],
        enviando: false,

        get itensJson() {
            return JSON.stringify(Object.values(this.selecionadosMap));
        },

        onFileChange(event) {
            const self = this;
            Array.from(event.target.files).forEach(function (f) {
                if (!self.arquivos.find(function (a) { return a.name === f.name; })) {
                    self.arquivos.push({ name: f.name, size: f.size, file: f });
                }
            });
            this._syncArquivos();
            setTimeout(function () {
                if (typeof lucide !== 'undefined') lucide.createIcons();
            }, 50);
        },

        removerArquivo(nome) {
            this.arquivos = this.arquivos.filter(function (a) { return a.name !== nome; });
            this._syncArquivos();
        },

        _syncArquivos() {
            const input = document.querySelector('input[name="arquivos"]');
            if (!input) return;
            try {
                const dt = new DataTransfer();
                this.arquivos.forEach(function (a) { dt.items.add(a.file); });
                input.files = dt.files;
            } catch (e) { /* navegador antigo: ignora */ }
        },

        fmtBytes(bytes) {
            if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
            if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return bytes + ' B';
        },

        enviarAprovacao() {
            const tipoEl = document.querySelector('select[name="tipo_ocorrencia"]');
            const responsavelEl = document.querySelector('select[name="responsavel_tipo"]');
            const tipo = tipoEl && tipoEl.value;
            const responsavel = responsavelEl && responsavelEl.value;
            const faltando = [];
            if (!this.notaOk) faltando.push('Nota Fiscal');
            if (!tipo) faltando.push('Tipo de Ocorrência');
            if (!this.motivo) faltando.push('Motivo');
            if (!this.causa) faltando.push('Causa');
            if (!responsavel) faltando.push('Responsável');
            if (faltando.length) {
                alert('Preencha os campos obrigatórios:\n• ' + faltando.join('\n• '));
                return;
            }
            document.getElementById('acao-input').value = 'concluir';
            document.getElementById('itens-json-input').value = JSON.stringify(Object.values(this.selecionadosMap));
            this.enviando = true;
            document.getElementById('form-ocorrencia').submit();
        }
    };
};

// Após HTMX trocar o conteúdo de #nota-info, lê o JSON de produtos e injeta no escopo Alpine.
function onNotaSwap(evt) {
    if (!evt.detail || !evt.detail.target || evt.detail.target.id !== 'nota-info') return;
    const json = document.getElementById('nota-produtos-json');
    const root = document.getElementById('ocorrencia-form-root');
    if (!root || !window.Alpine) return;
    const data = Alpine.$data(root);
    if (!data) return;
    if (json) {
        try {
            data.produtos = JSON.parse(json.textContent || '[]');
        } catch (e) {
            data.produtos = [];
        }
        data.notaOk = true;
        data.selecionadosMap = {};
    } else {
        data.produtos = [];
        data.notaOk = false;
        data.selecionadosMap = {};
    }
}

document.addEventListener('htmx:afterSwap', onNotaSwap);
