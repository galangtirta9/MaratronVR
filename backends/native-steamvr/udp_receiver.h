#ifndef MARATRON_UDP_RECEIVER_H
#define MARATRON_UDP_RECEIVER_H

#include <atomic>
#include <thread>
#include <string>
#include <netinet/in.h>

class UdpReceiver {
public:
    UdpReceiver();
    ~UdpReceiver();

    void start(int port = 9001);
    void stop();

    float move_x() const { return m_move_x.load(); }
    float move_y() const { return m_move_y.load(); }
    bool sprint() const { return m_sprint.load(); }

private:
    void listen();
    void apply_packet(const std::string &packet);

    std::atomic<bool> m_running{false};
    std::thread m_thread;
    int m_socket{-1};
    int m_port{9001};

    std::atomic<float> m_move_x{0.0f};
    std::atomic<float> m_move_y{0.0f};
    std::atomic<bool> m_sprint{false};
};

#endif