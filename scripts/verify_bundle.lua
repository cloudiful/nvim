local root = vim.fn.stdpath("config")
local specs = require("plugin_specs")
local lock = vim.json.decode(table.concat(vim.fn.readfile(root .. "/nvim-pack-lock.json"), "\n"))
local data_dir_name = vim.fn.has("win32") == 1 and "nvim-data" or "nvim"
local plugin_root = vim.fs.joinpath(root, ".data", data_dir_name, "site", "pack", "core", "opt")

local manifest_path = root .. "/tool-manifest.json"
local manifest = nil
if vim.fn.filereadable(manifest_path) == 1 then
  manifest = vim.json.decode(table.concat(vim.fn.readfile(manifest_path), "\n"))
  assert(manifest.profile == "full", "tool manifest must describe the full profile")
  assert(manifest.target and manifest.target ~= "", "tool manifest target is missing")
  for name, tool in pairs(manifest.tools or {}) do
    assert(tool.status == "bundled" or tool.status == "external" or tool.status == "unsupported", "Invalid tool status: " .. name)
    if tool.status == "bundled" then
      assert(tool.path and tool.path ~= "", "Bundled tool path is missing: " .. name)
      assert(vim.uv.fs_stat(root .. "/" .. tool.path), "Bundled tool is missing: " .. name)
      assert(tool.version and tool.version ~= "", "Bundled tool version is missing: " .. name)
      assert(tool.source_sha256 and tool.source_sha256:match("^[0-9a-fA-F]{64}$"), "Bundled tool checksum is missing: " .. name)
    end
  end
end

local function is_bundled(name)
  return manifest and manifest.tools and manifest.tools[name]
    and manifest.tools[name].status == "bundled"
end

local function bundled_command(name, args)
  assert(manifest, "Full profile manifest is required for bundled tool verification")
  local tool = assert(manifest.tools[name], "Missing tool manifest entry: " .. name)
  assert(tool.status == "bundled", "Tool is not bundled: " .. name)
  local command = { root .. "/" .. tool.path }
  assert(vim.fn.executable(command[1]) == 1, "Bundled tool is not executable: " .. name)
  for _, arg in ipairs(args or {}) do
    command[#command + 1] = arg
  end
  return command
end

local function run_tool(name, args, stdin)
  local result = vim.system(bundled_command(name, args), {
    stdin = stdin,
    text = true,
  }):wait()
  assert(result.code == 0, ("Tool failed: %s\n%s"):format(name, result.stderr or ""))
  return result
end

local function run_formatter(name, version_args, format_args, fixture)
  local version = run_tool(name, version_args)
  assert((version.stdout or "") ~= "" or (version.stderr or "") ~= "", "Formatter returned no version: " .. name)
  local result = run_tool(name, format_args, fixture)
  assert(result.stdout and result.stdout ~= "", "Formatter returned no output: " .. name)
end

local function run_formatter_if_bundled(name, version_args, format_args, fixture)
  if is_bundled(name) then
    run_formatter(name, version_args, format_args, fixture)
  end
end

local function lsp_initialize(name, args)
  if not is_bundled(name) then
    return
  end
  local initialize = vim.json.encode({
    jsonrpc = "2.0",
    id = 1,
    method = "initialize",
    params = {
      processId = vim.fn.getpid(),
      rootUri = "file:///tmp/nvim-bundle-verify",
      capabilities = {},
      clientInfo = { name = "nvim-bundle-verify", version = "1" },
    },
  })
  local initialized = vim.json.encode({ jsonrpc = "2.0", method = "initialized", params = {} })
  local shutdown = vim.json.encode({ jsonrpc = "2.0", id = 2, method = "shutdown", params = vim.NIL })
  local exit = vim.json.encode({ jsonrpc = "2.0", method = "exit", params = vim.NIL })
  local function frame(body)
    return ("Content-Length: %d\r\n\r\n%s"):format(#body, body)
  end
  local responses = 0
  local output = {}
  local errors = {}
  local exit_code
  local job = vim.fn.jobstart(bundled_command(name, args), {
    stdin = "pipe",
    stdout_buffered = false,
    on_stdout = function(_, data)
      for _, line in ipairs(data or {}) do
        if line:find("Content%-Length:") then
          responses = responses + 1
        end
        output[#output + 1] = line
      end
    end,
    on_stderr = function(_, data)
      for _, line in ipairs(data or {}) do
        errors[#errors + 1] = line
      end
    end,
    on_exit = function(_, code)
      exit_code = code
    end,
  })
  assert(job > 0, "Could not start LSP: " .. name)
  vim.fn.chansend(job, frame(initialize))
  assert(vim.wait(10000, function()
    return responses >= 1 or exit_code ~= nil
  end, 10), "LSP initialize timed out: " .. name)
  assert(responses >= 1, ("LSP exited during initialize: %s\n%s"):format(name, table.concat(errors, "\n")))
  vim.fn.chansend(job, frame(initialized))
  vim.fn.chansend(job, frame(shutdown))
  assert(vim.wait(10000, function()
    return responses >= 2 or exit_code ~= nil
  end, 10), "LSP shutdown timed out: " .. name)
  vim.fn.chansend(job, frame(exit))
  vim.fn.chanclose(job, "stdin")
  local result = vim.fn.jobwait({ job }, name == "tombi" and 2000 or 10000)[1]
  if result == -1 and name == "tombi" then
    -- Tombi completes the LSP exchange but may keep its runtime alive briefly.
    vim.fn.jobstop(job)
    result = 0
  end
  assert(result == 0, ("LSP failed: %s (%s)\n%s"):format(name, result, table.concat(errors, "\n")))
  assert(#output > 0, "LSP returned no output: " .. name)
end

if manifest and vim.env.BUNDLE_VERIFY_TOOLS == "1" then
  run_formatter_if_bundled("stylua", { "--version" }, { "--stdin-filepath", "fixture.lua", "-" }, "local   value=   { 1,2 }\n")
  run_formatter_if_bundled("rustfmt", { "--version" }, {}, "fn main(){let value=1;println!(\"{}\",value);}\n")
  -- gofmt has no version flag; -h verifies the fixed manifest binary before formatting.
  run_formatter_if_bundled("gofmt", { "-h" }, {}, "package main\nfunc main(){println(\"ok\")}\n")
  run_formatter_if_bundled("shfmt", { "--version" }, { "-" }, "#!/bin/sh\nif true;then echo ok;fi\n")
  run_formatter_if_bundled("prettier", { "--version" }, { "--stdin-filepath", "fixture.js" }, "const value={answer:42}\n")
  run_formatter_if_bundled("prettierd", { "--version" }, { "--stdin-filepath", "fixture.js" }, "const value={answer:42}\n")

  lsp_initialize("lua-language-server", {})
  lsp_initialize("rust-analyzer", {})
  lsp_initialize("bash-language-server", { "start" })
  lsp_initialize("docker-langserver", { "--stdio" })
  lsp_initialize("docker-compose-langserver", { "--stdio" })
  lsp_initialize("vscode-json-language-server", { "--stdio" })
  lsp_initialize("yaml-language-server", { "--stdio" })
  lsp_initialize("vscode-css-language-server", { "--stdio" })
  lsp_initialize("tombi", { "lsp" })
  lsp_initialize("vtsls", { "--stdio" })
  lsp_initialize("vue-language-server", { "--stdio" })
end

-- The checks above intentionally use the manifest. Linux musl releases, for
-- example, declare Node-based tools as external when no compatible Node asset
-- is available, so verification must not accidentally use the host PATH.

for _, spec in ipairs(specs.all()) do
  assert(lock.plugins[spec.name], "Missing lock entry: " .. spec.name)
  assert(vim.fn.isdirectory(plugin_root .. "/" .. spec.name) == 1, "Missing plugin: " .. spec.name)
end

local language_file = vim.env.TREESITTER_LANGUAGES_FILE or (root .. "/build/treesitter-languages.txt")
local languages = vim.fn.readfile(language_file)
for _, language in ipairs(languages) do
  local parser = root .. "/runtime/parser/" .. language .. ".so"
  local queries = root .. "/runtime/queries/" .. language
  assert(vim.uv.fs_stat(parser), "Missing parser: " .. language)
  assert(vim.uv.fs_stat(queries), "Missing queries: " .. language)
  if vim.env.TREESITTER_SKIP_LOAD ~= "1" then
    assert(pcall(vim.treesitter.language.add, language), "Cannot load parser: " .. language)
  end
end

local blink_root = plugin_root .. "/blink.cmp/target/release"
local extension = jit.os:lower() == "windows" and ".dll"
  or (jit.os:lower() == "mac" or jit.os:lower() == "osx") and ".dylib"
  or ".so"
local prefix = extension == ".dll" and "blink_cmp_fuzzy" or "libblink_cmp_fuzzy"
assert(vim.uv.fs_stat(blink_root .. "/" .. prefix .. extension), "Missing blink native library")

assert(pcall(require, "blink.cmp.fuzzy.rust"), "Cannot load blink native library")

local pack = require("pack")

pack.ensure("neo_tree")
assert(vim.fn.exists(":Neotree") == 2, "Neo-tree command is not registered")
vim.cmd("Neotree reveal")
vim.cmd("Neotree close")

pack.ensure("diffview")
for _, command_name in ipairs(specs.diffview_commands) do
  assert(vim.fn.exists(":" .. command_name) == 2, "Missing Diffview command: " .. command_name)
end

if manifest then
  pack.ensure("conform")
  local conform = require("conform")
  assert(conform.formatters_by_ft.lua, "Conform Lua formatter configuration is missing")
  assert(conform.formatters_by_ft.rust, "Conform Rust formatter configuration is missing")
  assert(conform.formatters.prettier, "Conform Prettier resolver is missing")
end

vim.cmd("edit docker-compose.yml")
assert(vim.bo.filetype == "yaml.docker-compose", "Compose filetype was not detected")

assert(vim.fn.maparg("[b", "n") ~= "", "Missing previous-buffer mapping")
assert(vim.fn.maparg("]b", "n") ~= "", "Missing next-buffer mapping")
assert(vim.fn.maparg(" bp", "n") == "", "Obsolete previous-buffer mapping still exists")
assert(vim.fn.maparg(" bn", "n") == "", "Obsolete next-buffer mapping still exists")
