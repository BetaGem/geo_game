import math

def haversine(lat1, lon1, lat2, lon2):
    """
    计算两点间球面距离（km）
    """
    R = 6371.0  # 地球半径，单位 km

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def km_offset(user_lat, user_lon, true_lat, true_lon):
    """
    返回 delta_lon_km, delta_lat_km
    """
    # 纬度每度 ~111 km
    delta_lat_km = (user_lat - true_lat) * 111.0
    # 经度每度 ~ cos(lat)*111 km
    avg_lat = (user_lat + true_lat) / 2
    delta_lon_km = (user_lon - true_lon) * 111.0 * math.cos(math.radians(avg_lat))
    
    return delta_lon_km, delta_lat_km