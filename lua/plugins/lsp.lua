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

-- Startup is latency-sensitive: resolving a tool spawns processes
-- (`mise which`, `node -e`), ~290ms for all servers. So at startup we only
-- build a filetype -> server map (pure Lua, no processes) and enable each
-- server lazily on the first buffer whose filetype needs it.
-- `vim.lsp.enable()` re-fires for already-open buffers, so `nvim file.rs`
-- still attaches correctly.
local servers = {
  lua_ls = { tool = "lua-language-server" },
  rust_analyzer = { tool = "rust-analyzer" },
  bashls = { tool = "bash-language-server", args = { "start" } },
  dockerls = { tool = "docker-langserver", args = { "--stdio" } },
  docker_compose_language_service = { tool = "docker-compose-langserver", args = { "--stdio" } },
  jsonls = { tool = "vscode-json-language-server", args = { "--stdio" } },
  tombi = { tool = "tombi", args = { "lsp" } },
  yamlls = { tool = "yaml-language-server", args = { "--stdio" } },
  nushell = { tool = "nu", args = { "--lsp" } },
  cssls = { tool = "vscode-css-language-server", args = { "--stdio" } },
  hyprls = { tool = "hyprls" },
  vue_ls = { tool = "vue-language-server", args = { "--stdio" } },
}

-- vtsls keeps its explicit filetype list (mirrors the base config).
local vtsls_filetypes = { 'typescript', 'javascript', 'javascriptreact', 'typescriptreact', 'vue' }

local function enable_simple(name)
  local spec = servers[name]
  local command = tools.command(spec.tool, spec.args)
  if not command then
    tools.explain(spec.tool)
    return false
  end
  vim.lsp.config(name, { cmd = command })
  vim.lsp.enable(name)
  return true
end

local function enable_vtsls()
  local vtsls_command = tools.command("vtsls", { "--stdio" })
  if not vtsls_command then
    tools.explain("vtsls")
    return false
  end
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
    filetypes = vtsls_filetypes,
  })
  vim.lsp.enable("vtsls")
  return true
end

local function enable_server(name)
  if name == "vtsls" then
    return enable_vtsls()
  end
  return enable_simple(name)
end

local pending = {}
local ft_to_servers = {}

local function register_filetypes(name, filetypes)
  if type(filetypes) ~= "table" then
    return false
  end
  for _, ft in ipairs(filetypes) do
    local list = ft_to_servers[ft]
    if not list then
      list = {}
      ft_to_servers[ft] = list
    end
    list[#list + 1] = name
  end
  return true
end

pending["vtsls"] = true
register_filetypes("vtsls", vtsls_filetypes)

for name in pairs(servers) do
  pending[name] = true
  local ok, cfg = pcall(function() return vim.lsp.config[name] end)
  if not (ok and register_filetypes(name, cfg and cfg.filetypes)) then
    -- Unknown server: preserve the old behavior and enable at startup.
    pending[name] = nil
    enable_server(name)
  end
end

vim.api.nvim_create_autocmd("FileType", {
  group = vim.api.nvim_create_augroup("UserLspLazy", { clear = true }),
  callback = function(args)
    local names = ft_to_servers[args.match]
    if not names then
      return
    end
    for _, name in ipairs(names) do
      if pending[name] then
        pending[name] = nil
        enable_server(name)
      end
    end
  end,
})
