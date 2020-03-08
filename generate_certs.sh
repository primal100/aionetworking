days=3650
base_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
base_ssl_dir=$base_dir/tests/test_networking/ssl
client_path=$base_ssl_dir/client
server_path=$base_ssl_dir/server

generate_certs () {
  key_path=$1/privkey.pem
  cert_path=$1/certificate.pem
  openssl req -newkey rsa:2048 -nodes -keyout "$key_path" -x509 -days $days -out "$cert_path"
}

generate_certs "$client_path"
generate_certs "$server_path"