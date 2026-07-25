-- Restore cursor position and window view when opening files
vim.api.nvim_create_autocmd("BufReadPost", {
    callback = function()
        local line = vim.fn.line("'\"")
        if line >= 1 and line <= vim.fn.line("$") then
            local filetype = vim.bo.filetype
            -- Skip certain filetypes
            if filetype ~= "commit" and filetype ~= "gitrebase" and filetype ~= "xxd" then
                if not vim.wo.diff then
                    vim.cmd('normal! g`"')
                end
            end
        end
    end,
})

-- Save view (cursor position, window scroll, etc.) when leaving a buffer
vim.api.nvim_create_autocmd("BufWinLeave", {
    pattern = "*",
    callback = function()
        if vim.fn.expand("%") ~= "" and vim.bo.buftype == "" then
            vim.cmd("mkview")
        end
    end,
})

-- Restore view when entering a buffer
vim.api.nvim_create_autocmd("BufWinEnter", {
    pattern = "*",
    callback = function()
        if vim.fn.expand("%") ~= "" and vim.bo.buftype == "" then
            vim.cmd("silent! loadview")
        end
    end,
})

-- Configure view options for better cursor position restoration
vim.opt.viewoptions = "folds,cursor,curdir,slash,unix"

-- Don't save options in views
vim.opt.viewdir = vim.fn.stdpath("cache") .. "/view"
