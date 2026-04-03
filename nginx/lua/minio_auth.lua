local hmac   = require "resty.openssl.hmac"
local digest = require "resty.openssl.digest"
local str    = require "resty.string"

local M = {}

local function sha256_hex(s)
    local d = digest.new("sha256")
    d:update(s)
    return str.to_hex(d:final())
end

local function hmac_sha256_raw(key, data)
    local h = hmac.new(key, "sha256")
    h:update(data)
    return h:final()
end

local function hmac_sha256_hex(key, data)
    return str.to_hex(hmac_sha256_raw(key, data))
end

function M.sign_request(access_key, secret_key, method, bucket, object_key)
    local host    = "minio:9000"
    local region  = "us-east-1"
    local service = "s3"

    local t        = os.time()
    local date_str = os.date("!%Y%m%d", t)
    local amz_date = os.date("!%Y%m%dT%H%M%SZ", t)

    local canonical_uri     = "/" .. bucket .. "/" .. object_key
    local canonical_headers = "host:" .. host .. "\nx-amz-date:" .. amz_date .. "\n"
    local signed_headers    = "host;x-amz-date"
    local payload_hash      = sha256_hex("")

    local canonical_request = method .. "\n"
            .. canonical_uri .. "\n"
            .. "\n"
            .. canonical_headers .. "\n"
            .. signed_headers .. "\n"
            .. payload_hash

    local credential_scope = date_str .. "/" .. region .. "/" .. service .. "/aws4_request"
    local string_to_sign   = "AWS4-HMAC-SHA256\n"
            .. amz_date .. "\n"
            .. credential_scope .. "\n"
            .. sha256_hex(canonical_request)

    local k_date    = hmac_sha256_raw("AWS4" .. secret_key, date_str)
    local k_region  = hmac_sha256_raw(k_date, region)
    local k_service = hmac_sha256_raw(k_region, service)
    local k_signing = hmac_sha256_raw(k_service, "aws4_request")
    local signature = hmac_sha256_hex(k_signing, string_to_sign)

    local authorization = "AWS4-HMAC-SHA256"
            .. " Credential=" .. access_key .. "/" .. credential_scope
            .. ", SignedHeaders=" .. signed_headers
            .. ", Signature=" .. signature

    return {
        authorization = authorization,
        amz_date      = amz_date,
    }
end

return M