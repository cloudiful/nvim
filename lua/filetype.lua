vim.api.nvim_create_autocmd({ "BufNewFile", "BufRead" }, {
    pattern = { "docker-compose.yml", "docker-compose.yaml" },
    command = "setfiletype yaml.docker-compose",
})
