local root = vim.fn.stdpath("config")
local specs = require("plugin_specs")
local lock = vim.json.decode(table.concat(vim.fn.readfile(root .. "/nvim-pack-lock.json"), "\n"))
local data_dir_name = vim.fn.has("win32") == 1 and "nvim-data" or "nvim"
local plugin_root = vim.fs.joinpath(root, ".data", data_dir_name, "site", "pack", "core", "opt")

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

vim.cmd("edit docker-compose.yml")
assert(vim.bo.filetype == "yaml.docker-compose", "Compose filetype was not detected")

assert(vim.fn.maparg("[b", "n") ~= "", "Missing previous-buffer mapping")
assert(vim.fn.maparg("]b", "n") ~= "", "Missing next-buffer mapping")
assert(vim.fn.maparg(" bp", "n") == "", "Obsolete previous-buffer mapping still exists")
assert(vim.fn.maparg(" bn", "n") == "", "Obsolete next-buffer mapping still exists")
