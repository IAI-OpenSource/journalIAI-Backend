local jwt        = require "resty.jwt"
local minio_auth = require "minio_auth"

local SECRET = STREAM_JWT_SECRET

local function reject(code, msg)
    ngx.log(ngx.WARN, "[STREAM_AUTH] " .. code .. " — " .. msg)
    ngx.status = code
    ngx.say(msg)
    ngx.exit(code)
end

-- 1. Token
local token = ngx.var.arg_token
if not token or token == "" then
    local auth = ngx.req.get_headers()["Authorization"]
    if auth then token = auth:match("Bearer%s+(.+)") end
end
if not token then return reject(401, "Token manquant") end

-- 2. Vérification JWT
local verified = jwt:verify(SECRET, token)
if not verified.verified then
    return reject(403, "Token invalide : " .. (verified.reason or "?"))
end

local payload = verified.payload

-- 3. Expiration
if not payload.exp or payload.exp < ngx.time() then
    return reject(401, "Token expiré")
end

-- 4. Validation UUID
local media_id = payload.media_id
if not media_id then return reject(403, "Token sans media_id") end

if not string.find(ngx.var.uri, media_id, 1, true) then
    return reject(403, "Token non valide pour cette ressource")
end

local uri_uuid = media_id

-- 5. Vérification type de ressource
local lua_prefix = ngx.var.lua_prefix
local target_bucket = ngx.var.target_bucket
local token_type = payload.resource_type
if token_type and token_type ~= lua_prefix then
    return reject(403, "Token de mauvais type")
end

-- 6. Construction object key MinIO
local object_key
local uri = ngx.var.uri

if lua_prefix == "processed-videos" then
    local pos = uri:find(uri_uuid, 1, true)
    if not pos then return reject(400, "URI HLS invalide") end
    local rest = uri:sub(pos + #uri_uuid + 1)
    if not rest or rest == "" then return reject(400, "URI HLS invalide") end
    object_key = "processed-videos/" .. uri_uuid .. "/" .. rest

elseif lua_prefix == "processed-images" then
    local pos = uri:find(uri_uuid, 1, true)
    if not pos then return reject(400, "URI image invalide") end
    local rest = uri:sub(pos + #uri_uuid + 1)
    if not rest or rest == "" then return reject(400, "URI image invalide") end
    object_key = "processed-images/" .. uri_uuid .. "/" .. rest
else
    return reject(400, "Type de ressource inconnu")
end

-- 7. Signature AWS SigV4
local ok, signed = pcall(
        minio_auth.sign_request,
        MINIO_ROOT_USER,
        MINIO_ROOT_PASSWORD,
        "GET",
        target_bucket,
        object_key
)
if not ok then
    ngx.log(ngx.ERR, "[STREAM_AUTH] Erreur signature : " .. tostring(signed))
    return reject(500, "Erreur interne")
end

ngx.req.set_header("Authorization", signed.authorization)
ngx.req.set_header("x-amz-date",    signed.amz_date)
ngx.req.set_header("host",          "minio:9000")

ngx.var.upstream_media_id = media_id