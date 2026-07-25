local root = vim.fn.stdpath("config")
local specs = require("plugin_specs")
local lock = vim.json.decode(table.concat(vim.fn.readfile(root .. "/nvim-pack-lock.json"), "\n"))
local plugin_root = root .. "/.data/nvim/site/pack/core/opt"

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
  assert(pcall(vim.treesitter.language.add, language), "Cannot load parser: " .. language)
end

local blink_root = plugin_root .. "/blink.cmp/target/release"
local extension = jit.os:lower() == "windows" and ".dll"
  or (jit.os:lower() == "mac" or jit.os:lower() == "osx") and ".dylib"
  or ".so"
local prefix = extension == ".dll" and "blink_cmp_fuzzy" or "libblink_cmp_fuzzy"
assert(vim.uv.fs_stat(blink_root .. "/" .. prefix .. extension), "Missing blink native library")
assert(vim.uv.fs_stat(blink_root .. "/version"), "Missing blink native version")

assert(pcall(require, "blink.cmp.fuzzy.rust"), "Cannot load blink native library")
