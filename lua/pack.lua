local specs = require("plugin_specs")

local M = {}
M.tools = require("tool_resolver")
local config_root = vim.fn.stdpath("config")
local data_dir_name = vim.fn.has("win32") == 1 and "nvim-data" or "nvim"
local bundled_site = vim.fs.joinpath(config_root, ".data", data_dir_name, "site")
local bundled_runtime = config_root .. "/runtime"

vim.opt.packpath:prepend(bundled_site)
vim.opt.runtimepath:prepend(bundled_runtime)

local configured = {}
local loaded = {}

local function require_configs(group)
  if configured[group] then
    return
  end

  local config = specs.configs[group]
  if not config then
    configured[group] = true
    return
  end

  if type(config) == "string" then
    require(config)
  else
    for _, module in ipairs(config) do
      require(module)
    end
  end
  configured[group] = true
end

local function plugin_path(name)
  return bundled_site .. "/pack/core/opt/" .. name
end

local function load_plugin(name)
  if vim.fn.isdirectory(plugin_path(name)) ~= 1 then
    error(("Missing bundled plugin %q. This source checkout is not built yet; run `uv run nvim-bundle package --target <target>` and install the resulting nvim bundle."):format(name))
  end
  vim.cmd.packadd({ name, magic = { file = false } })
end

local function add_group(group)
  if loaded[group] then
    return
  end

  local group_specs = specs.groups[group]
  if not group_specs then
    loaded[group] = true
    return
  end

  for _, spec in ipairs(group_specs) do
    load_plugin(spec.name)
  end
  loaded[group] = true
end

function M.ensure(group)
  add_group(group)
  require_configs(group)
end

local function diffview_wrapper(command_name)
  vim.api.nvim_create_user_command(command_name, function(opts)
    for _, name in ipairs(specs.diffview_commands) do
      pcall(vim.api.nvim_del_user_command, name)
    end

    M.ensure("diffview")

    local bang = opts.bang and "!" or ""
    local args = opts.args ~= "" and (" " .. opts.args) or ""
    vim.cmd(command_name .. bang .. args)
  end, {
    nargs = "*",
    bang = true,
  })
end

local function register_lazy_hooks()
  local group = vim.api.nvim_create_augroup("UserPackLoaders", { clear = true })

  local function maybe_load_gitsigns(buf, allow_unnamed)
    local name = vim.api.nvim_buf_get_name(buf)
    if vim.bo[buf].buftype == "" and (allow_unnamed or name ~= "") then
      M.ensure("gitsigns")
    end
  end

  vim.api.nvim_create_autocmd("VimEnter", {
    group = group,
    once = true,
    callback = function()
      vim.schedule(function()
        M.ensure("noice")
        M.ensure("which_key")
      end)
    end,
  })

  vim.api.nvim_create_autocmd({ "BufReadPre", "BufNewFile" }, {
    group = group,
    callback = function(args)
      maybe_load_gitsigns(args.buf, args.event == "BufNewFile")
    end,
  })

  vim.api.nvim_create_autocmd("FileType", {
    group = group,
    pattern = "markdown",
    callback = function()
      M.ensure("render_markdown")
    end,
  })

  vim.api.nvim_create_autocmd("FileType", {
    group = group,
    pattern = "java",
    callback = function(args)
      M.ensure("java")
      require("plugins.java").start_or_attach(args.buf)
    end,
  })

  for _, command_name in ipairs(specs.diffview_commands) do
    diffview_wrapper(command_name)
  end
end

local initialized = false

function M.setup()
  if initialized then
    return
  end
  initialized = true

  for _, group in ipairs(specs.startup_groups) do
    add_group(group)
  end

  for _, group in ipairs(specs.startup_configs) do
    require_configs(group)
  end

  register_lazy_hooks()
end

return M
