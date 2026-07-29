vim.api.nvim_create_autocmd('LspAttach', {
  group = vim.api.nvim_create_augroup('UserLspConfig', {}),
  callback = function(ev)
    local opts = { buffer = ev.buf }
    vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
    vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, opts)
    vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts)
    vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts)
    vim.keymap.set('n', '<F2>', vim.lsp.buf.rename, opts)
  end,
})

vim.diagnostic.config({
    virtual_text = true
})

local function enable_lsp(name, executable)
    if vim.fn.executable(executable) == 1 then
        vim.lsp.enable(name)
    end
end

enable_lsp("lua_ls", "lua-language-server")
enable_lsp("rust_analyzer", "rust-analyzer")
enable_lsp("bashls", "bash-language-server")
enable_lsp("docker_language_server", "docker-language-server")
enable_lsp("docker_compose_language_service", "docker-compose-langserver")
enable_lsp("jsonls", "vscode-json-language-server")
enable_lsp("tombi", "tombi")
enable_lsp("yamlls", "yaml-language-server")
enable_lsp("nushell", "nu")
enable_lsp("cssls", "vscode-css-language-server")
enable_lsp("hyprls", "hyprls")
local vue_language_server_path = vim.fn.expand(
'$HOME/.local/share/mise/installs/node/lts/lib/node_modules/@vue/language-server/')
local vue_plugin = {
    name = '@vue/typescript-plugin',
    location = vue_language_server_path,
    languages = { 'vue' },
    configNamespace = 'typescript',
    enableForWorkspaceTypeScriptVersions = true,
}
vim.lsp.config('vtsls', {
    cmd = { 'mise', 'exec', 'node@lts', '--', 'vtsls', '--stdio' },
    settings = {
        vtsls = {
            tsserver = {
                globalPlugins = {
                    vue_plugin,
                },
            },
        },
    },
    filetypes = { 'typescript', 'javascript', 'javascriptreact', 'typescriptreact', 'vue' },
})
vim.lsp.enable("vtsls")
vim.lsp.config('vue_ls', {
    cmd = { 'mise', 'exec', 'node@lts', '--', 'vue-language-server', '--stdio' }
})
vim.lsp.enable("vue_ls")
