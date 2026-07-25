local plugin_dir = assert(vim.env.TREESITTER_PLUGIN_DIR, "TREESITTER_PLUGIN_DIR is required")
local install_dir = assert(vim.env.TREESITTER_INSTALL_DIR, "TREESITTER_INSTALL_DIR is required")
local language_file = assert(vim.env.TREESITTER_LANGUAGES_FILE, "TREESITTER_LANGUAGES_FILE is required")

local languages = vim.fn.readfile(language_file)
if #languages == 0 then
  error("Tree-sitter language list is empty")
end

vim.opt.runtimepath:prepend(plugin_dir)

local install_lua = vim.fs.joinpath(plugin_dir, "lua", "nvim-treesitter", "install.lua")
local install_content = table.concat(vim.fn.readfile(install_lua), "\n")
if not install_content:find("local function find_extracted_dir", 1, true) then
  local helper = [[

---@param tmp string
---@param repo_project_name string
---@param dir_rev string
---@return string?
local function find_extracted_dir(tmp, repo_project_name, dir_rev)
  local expected = fs.joinpath(tmp, repo_project_name .. '-' .. dir_rev)
  if uv.fs_stat(expected) then
    return expected
  end

  local bare = fs.joinpath(tmp, repo_project_name)
  if uv.fs_stat(bare) then
    return bare
  end

  local directories = {}
  for entry in fs.dir(tmp) do
    local path = fs.joinpath(tmp, entry)
    local stat = uv.fs_stat(path)
    if stat and stat.type == 'directory' then
      table.insert(directories, path)
    end
  end

  if #directories == 1 then
    return directories[1]
  end
end
]]

  install_content = install_content:gsub(
    "\nlocal MAX_JOBS = 100",
    helper .. "\nlocal MAX_JOBS = 100",
    1
  )
  install_content = install_content:gsub(
    "local extracted = fs%.joinpath%(tmp, repo_project_name %.%. '%-' %.%. dir_rev%)",
    [[local extracted = find_extracted_dir(tmp, repo_project_name, dir_rev)
    if not extracted then
      return logger:error('Could not locate extracted parser source in %s', tmp)
    end]],
    1
  )
end

if not install_content:find("Keep downloaded parser sources for cross-compilation", 1, true) then
  local cleanup_block = [[
  -- clean up
  if repo and not repo.path then
    rmpath(fs.joinpath(cache_dir, project_name))
    a.schedule()
  end
]]
  if not install_content:find(cleanup_block, 1, true) then
    error("Unexpected nvim-treesitter cleanup layout")
  end
  install_content = install_content:gsub(
    vim.pesc(cleanup_block),
    "\n  -- Keep downloaded parser sources for cross-compilation.\n",
    1
  )
  vim.fn.writefile(vim.split(install_content, "\n", { plain = true }), install_lua)
end

local treesitter = require("nvim-treesitter")
treesitter.setup({ install_dir = install_dir })

local task = treesitter.install(languages, {
  force = true,
  max_jobs = tonumber(vim.env.TREESITTER_MAX_JOBS or "") or nil,
  summary = true,
})
local ok, result = task:pwait(1800000)
if not ok then
  error(result)
end
if not result then
  error("Tree-sitter parser installation failed")
end

local function copy_tree(source, target)
  local stat = vim.uv.fs_stat(source)
  if not stat then
    error("Missing Tree-sitter query source: " .. source)
  end

  if stat.type == "file" then
    vim.fn.mkdir(vim.fs.dirname(target), "p")
    assert(vim.uv.fs_copyfile(source, target))
    return
  end

  vim.fn.mkdir(target, "p")
  for name in vim.fs.dir(source) do
    copy_tree(
      vim.fs.joinpath(source, name),
      vim.fs.joinpath(target, name)
    )
  end
end

local query_root = vim.fs.joinpath(install_dir, "queries")
local query_sources = {}
for language in vim.fs.dir(query_root) do
  local query_path = vim.fs.joinpath(query_root, language)
  query_sources[language] = vim.uv.fs_realpath(query_path) or query_path
end
vim.fs.rm(query_root, { recursive = true, force = true })

for language, query_source in pairs(query_sources) do
  copy_tree(query_source, vim.fs.joinpath(query_root, language))
end

vim.fs.rm(vim.fs.joinpath(install_dir, "parser-info"), { recursive = true, force = true })

for _, language in ipairs(languages) do
  local parser = vim.fs.joinpath(install_dir, "parser", language .. ".so")
  if not vim.uv.fs_stat(parser) then
    error("Missing built Tree-sitter parser: " .. parser)
  end
end
