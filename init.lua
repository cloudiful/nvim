require('keymaps')
require('auto_restore')
require('filetype')
require('pack').setup()

vim.opt.relativenumber = true
-- vim.opt.cursorline = true
vim.opt.undofile = true

vim.opt.termguicolors = true

vim.cmd.colorscheme("catppuccin-mocha")

vim.o.winborder = "rounded"

vim.opt.expandtab = true
vim.opt.shiftwidth = 4

vim.opt.foldlevel = 99
vim.opt.foldlevelstart = 99

vim.opt.foldcolumn = "1"
vim.opt.fillchars = {
    eob = " ",
    fold = " ",
    foldopen = "",
    foldsep = " ",
    foldclose = "",
}

vim.opt.ignorecase = true

vim.opt.scrolloff = 10
