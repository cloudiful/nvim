local M = {}

local root_markers = { "mvnw", "gradlew", ".git" }

local function project_root(jdtls, buf)
    return jdtls.setup.find_root(root_markers, vim.api.nvim_buf_get_name(buf))
end

local function workspace_dir(root_dir)
    local project_name = vim.fn.fnamemodify(root_dir, ":t")
        :gsub("[^%w_.-]", "_")
    local project_hash = vim.fn.sha256(root_dir)
    return vim.fs.joinpath(
        vim.fn.stdpath("cache"),
        "jdtls",
        project_name .. "-" .. project_hash
    )
end

local function java_keymaps(jdtls, buf)
    local function map(mode, lhs, rhs, desc)
        vim.keymap.set(mode, lhs, rhs, { buffer = buf, silent = true, desc = desc })
    end

    map("n", "<leader>jo", jdtls.organize_imports, "Organize imports")
    map("n", "<leader>jv", function()
        jdtls.extract_variable()
    end, "Extract variable")
    map("v", "<leader>jv", function()
        jdtls.extract_variable(true)
    end, "Extract variable")
    map("n", "<leader>jc", function()
        jdtls.extract_constant()
    end, "Extract constant")
    map("v", "<leader>jc", function()
        jdtls.extract_constant(true)
    end, "Extract constant")
    map("v", "<leader>jm", function()
        jdtls.extract_method(true)
    end, "Extract method")
end

function M.start_or_attach(buf)
    buf = buf or vim.api.nvim_get_current_buf()

    if vim.fn.executable("jdtls") ~= 1 then
        vim.notify(
            "jdtls is not available in PATH; Java LSP is disabled for this buffer",
            vim.log.levels.WARN
        )
        return
    end

    local jdtls = require("jdtls")
    local root_dir = project_root(jdtls, buf)
    if not root_dir then
        vim.notify(
            "Java project root not found (expected mvnw, gradlew, or .git)",
            vim.log.levels.INFO
        )
        return
    end

    local data_dir = workspace_dir(root_dir)
    vim.fn.mkdir(data_dir, "p")

    local config = {
        cmd = { "jdtls", "-data", data_dir },
        root_dir = root_dir,
        settings = {
            java = {},
        },
        init_options = {
            bundles = {},
        },
        on_attach = function(_, attached_buf)
            java_keymaps(jdtls, attached_buf)
        end,
    }

    vim.api.nvim_buf_call(buf, function()
        jdtls.start_or_attach(config)
    end)
end

return M
