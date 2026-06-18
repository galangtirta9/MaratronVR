def clamp(value, low, high):
    return max(low, min(high, value))


def normalize_curve_points(points):
    clean = []
    for x, y in points:
        clean.append([clamp(float(x), 0.0, 1.0), clamp(float(y), 0.0, 1.0)])

    clean.sort(key=lambda p: p[0])

    if not clean or clean[0][0] != 0.0:
        clean.insert(0, [0.0, 0.0])

    if clean[-1][0] != 1.0:
        clean.append([1.0, 1.0])

    clean[0] = [0.0, clamp(clean[0][1], 0.0, 1.0)]
    clean[-1] = [1.0, clamp(clean[-1][1], 0.0, 1.0)]

    deduped = []
    for point in clean:
        if deduped and abs(deduped[-1][0] - point[0]) < 0.0001:
            deduped[-1] = point
        else:
            deduped.append(point)

    return deduped


def apply_curve(value, points):
    value = clamp(abs(float(value)), 0.0, 1.0)
    points = normalize_curve_points(points)

    for index in range(len(points) - 1):
        x1, y1 = points[index]
        x2, y2 = points[index + 1]

        if x1 <= value <= x2:
            if abs(x2 - x1) < 0.0001:
                return y2
            t = (value - x1) / (x2 - x1)
            return y1 + (y2 - y1) * t

    return points[-1][1]