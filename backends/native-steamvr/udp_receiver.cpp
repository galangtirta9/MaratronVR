#include "udp_receiver.h"

#include <cstdio>
#include <cstring>
#include <string>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/time.h>

static float clamp(float v) {
    if (v < -1.0f) return -1.0f;
    if (v > 1.0f) return 1.0f;
    return v;
}

static float read_float(const std::string &packet, const std::string &key, float fallback) {
    std::string token = "\"" + key + "\"";
    auto key_pos = packet.find(token);
    if (key_pos == std::string::npos) return fallback;
    auto colon = packet.find(':', key_pos + token.size());
    if (colon == std::string::npos) return fallback;
    try {
        return std::stof(packet.substr(colon + 1));
    } catch (...) {
        return fallback;
    }
}

static bool read_bool(const std::string &packet, const std::string &key, bool fallback) {
    std::string token = "\"" + key + "\"";
    auto key_pos = packet.find(token);
    if (key_pos == std::string::npos) return fallback;
    auto colon = packet.find(':', key_pos + token.size());
    if (colon == std::string::npos) return fallback;
    return packet.substr(colon + 1, 6).find("true") != std::string::npos;
}

UdpReceiver::UdpReceiver() {}
UdpReceiver::~UdpReceiver() { stop(); }

void UdpReceiver::start(int port) {
    if (m_running.exchange(true)) return;
    m_port = port;
    std::fprintf(stderr, "[maratron] UdpReceiver starting on 127.0.0.1:%d\n", port);
    m_thread = std::thread(&UdpReceiver::listen, this);
}

void UdpReceiver::stop() {
    if (!m_running.exchange(false)) return;
    if (m_socket >= 0) {
        ::shutdown(m_socket, SHUT_RDWR);
        ::close(m_socket);
        m_socket = -1;
    }
    if (m_thread.joinable()) m_thread.join();
    m_move_y.store(0.0f);
    m_sprint.store(false);
    std::fprintf(stderr, "[maratron] UdpReceiver stopped\n");
}

void UdpReceiver::listen() {
    m_socket = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (m_socket < 0) {
        std::fprintf(stderr, "[maratron] UdpReceiver socket() failed\n");
        m_running = false;
        return;
    }

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(m_port);

    if (::bind(m_socket, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) < 0) {
        std::fprintf(stderr, "[maratron] UdpReceiver bind() failed on 127.0.0.1:%d\n", m_port);
        ::close(m_socket);
        m_socket = -1;
        m_running = false;
        return;
    }

    std::fprintf(stderr, "[maratron] UdpReceiver listening on 127.0.0.1:%d\n", m_port);

    // Set receive timeout so we can check m_running periodically
    struct timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = 100000; // 100ms
    ::setsockopt(m_socket, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    while (m_running.load()) {
        char buffer[512] = {0};
        ssize_t received = ::recv(m_socket, buffer, sizeof(buffer) - 1, 0);
        if (received > 0) {
            apply_packet(std::string(buffer, static_cast<size_t>(received)));
        }
    }
}

void UdpReceiver::apply_packet(const std::string &packet) {
    float x = read_float(packet, "move_x", 0.0f);
    float y = read_float(packet, "move_y", 0.0f);
    m_move_x.store(clamp(x));
    m_move_y.store(clamp(y));

    bool s = read_bool(packet, "sprint", false);
    m_sprint.store(s);
}
