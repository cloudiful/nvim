local parser_runtime = vim.fn.stdpath("config") .. "/runtime"
local parser_dir = parser_runtime .. "/parser"
local query_dir = parser_runtime .. "/queries"

if vim.fn.isdirectory(parser_dir) ~= 1 or vim.fn.isdirectory(query_dir) ~= 1 then
  vim.notify("Bundled Tree-sitter runtime is missing", vim.log.levels.WARN)
  return
end

local supported_languages = {
  bash = true,
  c = true,
  cpp = true,
  css = true,
  diff = true,
  dockerfile = true,
  gitcommit = true,
  gitignore = true,
  go = true,
  html = true,
  java = true,
  javascript = true,
  json = true,
  json5 = true,
  lua = true,
  markdown = true,
  markdown_inline = true,
  nu = true,
  powershell = true,
  python = true,
  query = true,
  regex = true,
  rust = true,
  sql = true,
  toml = true,
  tsx = true,
  typescript = true,
  vim = true,
  vimdoc = true,
  vue = true,
  xml = true,
  yaml = true,
}

local treesitter_group = vim.api.nvim_create_augroup("UserTreesitterAttach", { clear = true })
local failed_languages = {}

local function attach_treesitter(args)
  local buf = args.buf
  local filetype = vim.bo[buf].filetype
  local lang = vim.treesitter.language.get_lang(filetype)
  if not lang or not supported_languages[lang] or failed_languages[lang] then
    return
  end

  local ok = pcall(vim.treesitter.start, buf, lang)
  if not ok then
    failed_languages[lang] = true
    return
  end

  if vim.api.nvim_get_current_buf() == buf then
    vim.wo.foldexpr = "v:lua.vim.treesitter.foldexpr()"
    vim.wo.foldmethod = "expr"
  end
end

vim.api.nvim_create_autocmd({ "FileType", "BufEnter", "BufWinEnter" }, {
  group = treesitter_group,
  callback = attach_treesitter,
})
