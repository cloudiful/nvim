vim.g.mapleader = ' '

vim.opt.clipboard = "unnamedplus"

local clipboard_key = "C"
if vim.fn.has("mac") == 1 then
    clipboard_key = "D"
end

local function map(mode, lhs, rhs, desc, opts)
    local options = vim.tbl_extend("force", { noremap = true, silent = true }, opts or {})
    if desc then
        options.desc = desc
    end
    vim.keymap.set(mode, lhs, rhs, options)
end

local function get_project_root()
    local buffer_path = vim.fn.expand('%:p')
    local cwd

    if vim.bo.filetype == 'netrw' and vim.b.netrw_curdir then
        cwd = vim.b.netrw_curdir
    elseif vim.fn.isdirectory(buffer_path) == 1 then
        cwd = buffer_path
    elseif buffer_path ~= "" then
        cwd = vim.fn.expand('%:p:h')
    else
        cwd = vim.fn.getcwd()
    end

    if cwd then
        local root = vim.fs.find({
            '.git',
            'Makefile',
            'package.json',
            'go.mod',
            'Cargo.toml',
            'docker-compose.yaml',
            'docker-compose.yml',
        }, { path = cwd, upward = true })[1]

        if root then
            cwd = vim.fs.dirname(root)
        end
    end
    return cwd
end

local function ensure_fzf()
    require("pack").ensure("fzf")
    return require("fzf-lua")
end

local function ensure_conform()
    require("pack").ensure("conform")
    return require("conform")
end

local function close_buffer()
    local current_buf = vim.api.nvim_get_current_buf()

    if vim.bo[current_buf].modified then
        vim.notify('Buffer has unsaved changes; save or discard them first', vim.log.levels.WARN)
        return
    end

    local alternate_buf = vim.fn.bufnr('#')

    if vim.api.nvim_buf_is_valid(alternate_buf) then
        vim.api.nvim_set_current_buf(alternate_buf)
    else
        vim.cmd('bprevious')
        if current_buf == vim.api.nvim_get_current_buf() then
            vim.api.nvim_win_close(0, false)
        end
    end

    vim.api.nvim_buf_delete(current_buf, {})
end

map('n', '<leader>e', function()
    require("pack").ensure("neo_tree")
    if vim.bo.filetype == "neo-tree" then
        vim.cmd("Neotree close")
    else
        vim.cmd("Neotree reveal")
    end
end, 'Explorer')

map({ 'n', 'v' }, '<leader>ff', function()
    ensure_fzf().files({ cwd = get_project_root() })
end, 'Find files')

map({ 'n', 'v' }, '<leader>fg', function()
    ensure_fzf().live_grep({ cwd = get_project_root() })
end, 'Live grep')

map('n', '<leader>fr', function()
    ensure_fzf().oldfiles()
end, 'Recent files')

map({ 'n', 'v' }, '<leader>fm', function()
    ensure_conform().format()
end, 'Format')

map('n', '<leader>bb', function()
    ensure_fzf().buffers()
end, 'Buffers')

map('n', '<leader>bd', close_buffer, 'Delete buffer')

map('n', '<leader>rn', function()
    vim.lsp.buf.rename()
end, 'Rename')

map('n', '<leader>ca', function()
    vim.lsp.buf.code_action()
end, 'Code action')

map('n', '<leader>?', function()
    require("which-key").show({ keys = "<leader>", loop = true })
end, 'Leader keymaps')

map('n', '<Home>', '^', 'Move to first non-blank char')
map('x', 'd', '"_d', 'Delete without yanking')

map('v', '<' .. clipboard_key .. '-c>', '"+y', 'Copy')
map({ 'n', 'i', 'v' }, '<' .. clipboard_key .. '-s>', function()
    vim.cmd('update')
end, 'Save')
map({ 'n', 'i', 'v' }, '<' .. clipboard_key .. '-z>', function()
    vim.cmd('undo')
end, 'Undo')
map({ 'n', 'i', 'v' }, '<' .. clipboard_key .. '-S-z>', function()
    vim.cmd('redo')
end, 'Redo')

map('n', '[d', function()
    vim.diagnostic.goto_prev()
end, 'Previous diagnostic')

map('n', ']d', function()
    vim.diagnostic.goto_next()
end, 'Next diagnostic')

map('n', '[b', function()
    vim.cmd('bprevious')
end, 'Previous buffer')

map('n', ']b', function()
    vim.cmd('bnext')
end, 'Next buffer')
