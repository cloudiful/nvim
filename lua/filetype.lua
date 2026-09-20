vim.api.nvim_create_autocmd({ "BufNewFile", "BufRead" }, {
    pattern = { "docker-compose.yml", "docker-compose.yaml" },
    command = "set ft=yaml.docker-compose",
})

-- chezmoi templates: strip the trailing `.tmpl` and detect the real type,
-- so `opencode.jsonc.tmpl` behaves like `opencode.jsonc`.
vim.api.nvim_create_autocmd({ "BufNewFile", "BufRead" }, {
    pattern = "*.tmpl",
    callback = function(args)
        local stripped = args.file:gsub("%.tmpl$", "")
        if stripped == args.file then
            return
        end
        local ft = vim.filetype.match({ filename = stripped })
        if ft then
            vim.bo[args.buf].filetype = ft
        end
    end,
})

-- The portable bundle ships no `jsonc` parser; reuse `json` for highlighting.
vim.treesitter.language.register("json", "jsonc")
