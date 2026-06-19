using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using HIDMaestro;

namespace MaratronBridge;

/// <summary>
/// MaratronBridge.exe — receives movement data from the Maratron Python GUI
/// over UDP and pushes it to a HIDMaestro virtual gamepad on Windows.
///
/// Build: dotnet build -c Release
/// Run:   MaratronBridge.exe [port] [profileName]
///        Default port = 9003, profile = "generic-dinput-gamepad"
/// </summary>
class Program
{
    static void Main(string[] args)
    {
        int port = args.Length > 0 ? int.Parse(args[0]) : 9003;
        string profileName = args.Length > 1 ? args[1] : "generic-dinput-gamepad";
        string controllerName = "Maratron Treadmill";

        Console.WriteLine($"[MaratronBridge] Starting on UDP port {port}, profile={profileName}");

        // ── HIDMaestro setup ────────────────────────────────────────────
        using var ctx = new HMContext();
        ctx.LoadDefaultProfiles();

        // Install driver on first run (admin required once per machine)
        if (!ctx.IsDriverInstalled)
        {
            Console.WriteLine("[MaratronBridge] Installing HIDMaestro driver (requires admin)...");
            ctx.InstallDriver();
        }

        var profile = ctx.GetProfile(profileName);
        if (profile == null)
        {
            Console.Error.WriteLine($"[MaratronBridge] Profile '{profileName}' not found. Available:");
            foreach (var p in ctx.Profiles)
                Console.Error.WriteLine($"  {p.Id}");
            Environment.Exit(1);
        }

        using var controller = ctx.CreateController(profile);

        // Override the controller name shown in joy.cpl / DirectInput
        HMOemNameOverride.Set(profile.VendorId, profile.ProductId, controllerName);
        Console.WriteLine($"[MaratronBridge] Virtual controller '{controllerName}' created (VID:{profile.VendorId:X4} PID:{profile.ProductId:X4})");

        // ── UDP listener ────────────────────────────────────────────────
        using var udp = new UdpClient(port);
        var remote = new IPEndPoint(IPAddress.Any, 0);
        var state = new HMGamepadState();
        var axes = new Dictionary<HMAxis, float>();

        Console.WriteLine($"[MaratronBridge] Listening on 127.0.0.1:{port}...");

        while (true)
        {
            try
            {
                byte[] data = udp.Receive(ref remote);
                string json = Encoding.UTF8.GetString(data);
                var packet = JsonSerializer.Deserialize<MovementPacket>(json);
                if (packet == null) continue;

                // Map 0..1 (normalized) to HIDMaestro axes
                // For signed centered axes: 0.5 = center
                // move_x: -1..+1 → 0..1 (0.5 = center)
                float lx = (float)((packet.move_x + 1.0) / 2.0);
                float ly = (float)((packet.move_y + 1.0) / 2.0);

                axes[HMAxis.X] = Math.Clamp(lx, 0.0f, 1.0f);
                axes[HMAxis.Y] = Math.Clamp(ly, 0.0f, 1.0f);

                state.Axes = axes;
                state.Buttons = packet.sprint ? HMButton.LeftStick : HMButton.None;

                controller.SubmitState(state);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"[MaratronBridge] Error: {ex.Message}");
            }
        }
    }
}

/// <summary>Matches the JSON sent by hidmaestro_backend.py</summary>
class MovementPacket
{
    public double move_x { get; set; }
    public double move_y { get; set; }
    public bool sprint { get; set; }
}