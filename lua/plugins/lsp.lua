local tools = require("pack").tools

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
  virtual_text = true,
})

local function enable_lsp(name, tool, args)
  local command = tools.command(tool, args)
  if not command then
    tools.explain(tool)
    return false
  end
  vim.lsp.config(name, { cmd = command })
  vim.lsp.enable(name)
  return true
end

enable_lsp("lua_ls", "lua-language-server")
enable_lsp("rust_analyzer", "rust-analyzer")
enable_lsp("bashls", "bash-language-server", { "start" })
enable_lsp("dockerls", "docker-langserver", { "--stdio" })
enable_lsp("docker_compose_language_service", "docker-compose-langserver", { "--stdio" })
enable_lsp("jsonls", "vscode-json-language-server", { "--stdio" })
enable_lsp("tombi", "tombi", { "lsp" })
enable_lsp("yamlls", "yaml-language-server", { "--stdio" })
enable_lsp("nushell", "nu", { "--lsp" })
enable_lsp("cssls", "vscode-css-language-server", { "--stdio" })
enable_lsp("hyprls", "hyprls")

local vtsls_command = tools.command("vtsls", { "--stdio" })
if vtsls_command then
  local settings = {
    vtsls = {
      tsserver = {
        globalPlugins = {},
      },
    },
  }
  local vue_plugin_path = tools.vue_plugin()
  if vue_plugin_path then
    settings.vtsls.tsserver.globalPlugins[1] = {
      name = '@vue/typescript-plugin',
      location = vue_plugin_path,
      languages = { 'vue' },
      configNamespace = 'typescript',
      enableForWorkspaceTypeScriptVersions = true,
    }
  else
    tools.explain("@vue/typescript-plugin")
  end
  vim.lsp.config('vtsls', {
    cmd = vtsls_command,
    settings = settings,
    filetypes = { 'typescript', 'javascript', 'javascriptreact', 'typescriptreact', 'vue' },
  })
  vim.lsp.enable("vtsls")
else
  tools.explain("vtsls")
end

enable_lsp("vue_ls", "vue-language-server", { "--stdio" })
