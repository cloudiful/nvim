require("neo-tree").setup({
    close_if_last_window = true,
    filesystem = {
        hijack_netrw_behavior = "open_default",
        follow_current_file = {
            enabled = true,
            leave_dirs_open = false,
        },
        window = {
            mappings = {
                ["/"] = "fuzzy_finder",
                ["H"] = "toggle_hidden",
                ["<bs>"] = "navigate_up",
                ["."] = "set_root",
                ["P"] = {
                    "toggle_preview",
                    config = {
                        use_float = false,
                    },
                },
            },
        },
    },
})

-- In directory-started sessions (`nvim <dir>` with open_default), quitting
-- the tree would strand an empty unnamed buffer. Quit Neovim instead.
-- Scoped by `vim.g.started_with_directory` (set in pack.lua), so plain
-- `nvim` / `nvim <file>` sessions are never affected. A lone tree window
-- is left to `close_if_last_window`.
vim.api.nvim_create_autocmd({ "BufEnter", "WinClosed" }, {
    group = vim.api.nvim_create_augroup("UserNeoTreeSmartQuit", { clear = true }),
    callback = function()
        if not vim.g.started_with_directory then
            return
        end
        vim.schedule(function()
            local wins = vim.api.nvim_list_wins()
            if #wins ~= 1 then
                return
            end
            local buf = vim.api.nvim_win_get_buf(wins[1])
            if vim.bo[buf].filetype == "neo-tree" then
                return
            end
            if vim.api.nvim_buf_get_name(buf) ~= "" then
                return
            end
            if vim.bo[buf].buftype ~= "" or vim.bo[buf].modified then
                return
            end
            if vim.api.nvim_buf_line_count(buf) ~= 1 then
                return
            end
            if vim.api.nvim_buf_get_lines(buf, 0, 1, false)[1] ~= "" then
                return
            end
            vim.cmd("quit")
        end)
    end,
})
