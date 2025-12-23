import bpy
import math
import sys
import os
import json
from mathutils import Vector, Euler, Matrix
import bmesh
import yaml
import ast
import random
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union

COLORS = {
    "red": [1, 0, 0, 1],
    "green": [0, 1, 0, 1],
    "blue": [0, 0.25, 1, 1],
    "yellow": [1, 1, 0, 1],
    "purple": [1, 0, 1, 1],
    "cyan": [0, 1, 1, 1],
    "orange": [1, 0.5, 0, 1],
    "white": [1, 1, 1, 1],
    "gray": [0.5, 0.5, 0.5, 1],
    "black": [0, 0, 0, 1],
    # --- 新增以下两行 ---
    "dark_gray": [0.3, 0.3, 0.3, 1],   # 深灰 (替代红色区域)
    "light_gray": [0.6, 0.6, 0.6, 1]      # 浅灰 (替代绿色区域)
    }

MATERIALS = {
    'wood': {
        1: 0.05,
        2: 0.9,
        3: 2
    },
}

class Heightmap:
    def __init__(self):
        self.height = {}
        self.height_list = []

    def update_heightmap(self, position, size, rotation):
        """
        Update the heightmap with a block at a given position and size.
        """
        polygon = self.get_polygon(position, size, rotation)
        if position[2] != 0.75:
            pos_polygon = self.height[position[2]-size[2]/2]
            update = pos_polygon.difference(polygon)
            self.height[position[2]-size[2]/2] = update

        new_height = position[2] + size[2]/2
        if new_height not in self.height_list:
            self.height_list.append(new_height)
            self.height_list = sorted(self.height_list)
            self.height[new_height] = polygon
        else:
            current_multipolygon = self.height[new_height]
            if current_multipolygon.intersects(polygon):
                raise ValueError("polygons intersect!")

            new_multipoly = current_multipolygon.union(polygon)
            self.height[new_height] = new_multipoly

    def get_polygon(self, position, size, rotation):
        """
        Calculate the support area for a block on the heightmap.
        Only when the ratio is enough, the block can be placed.
        """
        l, w = size[0], size[1]
        angle = rotation[2]

        # Calculate the corners of the block in world coordinates
        corners = [
            (position[0] + l/2 * np.cos(angle) - w/2 * np.sin(angle),
             position[1] + l/2 * np.sin(angle) + w/2 * np.cos(angle)),
            (position[0] + l/2 * np.cos(angle) + w/2 * np.sin(angle),
             position[1] + l/2 * np.sin(angle) - w/2 * np.cos(angle)),
            (position[0] - l/2 * np.cos(angle) + w/2 * np.sin(angle),
             position[1] - l/2 * np.sin(angle) - w/2 * np.cos(angle)),
            (position[0] - l/2 * np.cos(angle) - w/2 * np.sin(angle),
             position[1] - l/2 * np.sin(angle) + w/2 * np.cos(angle))
        ]

        # Create a polygon from the corners
        polygon = Polygon(corners)
        return polygon

    def calculate_plane(self, degree, gray_tone, point=None):
        degree = math.radians(degree)
        if gray_tone == 'light_gray':
            normal = (-math.sin(degree), 0, math.cos(degree))
            if not point:
                point = (-1.5, 0, 2.5)
        else:
            normal = (math.sin(degree), 0, math.cos(degree))
            if not point:
                point = (1.5, 0, 2.5)

        a = normal[0]
        b = 0
        c = normal[2]
        d = - a * point[0] - c * point[2]
        return a, b, c, d


    def generate_points_on_plane(self, size, degree, gray_tone, n_points=20, noise_level=2):
        a, b, c, d = self.calculate_plane(degree, gray_tone)

        x = np.random.uniform(PROJECTION_X[0], PROJECTION_X[1], n_points)
        y = np.random.uniform(PROJECTION_Y[0], PROJECTION_Y[1], n_points)

        z_plane = (-a*x - b*y - d) / c

        noise = np.random.normal(0, noise_level, n_points)

        X = np.column_stack([x, y, np.ones_like(x)])
        coefficients = np.linalg.lstsq(X, noise, rcond=None)[0]
        adjusted_noise = noise - X.dot(coefficients)

        z = z_plane + adjusted_noise

        processed_z = []
        for z_val in z:
            flag = False
            for i in range(len(self.height_list)):
                if i == 0:
                    h = self.height_list[i]
                    if z_val < h:
                        processed_z.append(self.height_list[i]+size[2]/2)
                        flag = True
                        break
                elif i<len(self.height_list):
                    h = self.height_list[i]
                    if z_val < h:
                        processed_z.append(self.height_list[i-1]+size[2]/2)
                        flag = True
                        break
            if flag == False:
                processed_z.append(self.height_list[-1]+size[2]/2)
        positions = [(float(x[i]), float(y[i]), float(processed_z[i])) for i in range(n_points)]
        return positions

    # def get_valid_positions(self, size, rotation, flag, gray_tone):
    #     """Get all valid positions on the heightmap."""
    #     valid_counts = 0
    #     valid_positions = []
    #     while valid_counts < 80:
    #         if flag == 1:
    #             # ==========================================
    #             # 修改部分：基座生成逻辑
    #             # ==========================================
    #             # 原逻辑：根据 gray_tone 判断 x 范围是 (-1.5, 0) 还是 (0, 1.5)
    #             # 新逻辑：无视 gray_tone，直接在分界线(x=0)附近随机生成
    #             # 这里设置范围为 [-0.5, 0.5]，你可以根据需要调整这个宽度
    #             x = np.random.uniform(-0.75, 0.75) 
                
    #             # y 轴范围保持不变
    #             y = np.random.uniform(-0.75, 0.75)
    #             z = 0.75
                
    #             position = (x, y, z)
    #             new_polygon = self.get_polygon(position, size, rotation)
    #             valid_positions.append(position)
    #             valid_counts += 1
    #             # ==========================================
    #         else:
    #             positions = self.generate_points_on_plane(size, DEGREE, gray_tone)
    #             for position in positions:
    #                 new_polygon = self.get_polygon(position, size, rotation)
    #                 pos_multipoly = self.height[position[2]-size[2]/2]
    #                 if pos_multipoly.intersection(new_polygon).area >= INTERSECTION_THRESHOLD:
    #                     #if pos_multipoly.intersects(new_polygon):
    #                     valid_positions.append(position)
    #                     valid_counts += 1
    #     sorted_positions = sorted(valid_positions, key=lambda t:t[2])
    #     return sorted_positions
    
    def get_valid_positions(self, size, rotation, flag, gray_tone):
        """
        [核心修改] 获取有效位置：
        不再贪婪地寻找最高点的中心，而是尝试在顶部的几层中随机寻找有效支撑点。
        """
        valid_counts = 0
        valid_positions = []
        is_stable_mode = True

        while valid_counts < 80:
            if flag == 1:
                # --- 基座逻辑：稍微扩大基座范围，为上层多样性打基础 ---
                # 范围从 0.5 扩大到 0.8
                x = np.random.uniform(-0.75, 0.75) 
                y = np.random.uniform(-0.75, 0.75)
                z = 0.75
                position = (x, y, z)
                valid_positions.append(position)
                valid_counts += 1
            else:
                # --- 堆叠逻辑 (改进版) ---
                positions = []
                
                if is_stable_mode and self.height_list:
                    # [策略修改 1]: 多层级选择
                    # 以前只选 self.height_list[-1] (最高层)
                    # 现在我们看最后 3 层 (如果有的话)，给予不同的权重
                    
                    num_layers = len(self.height_list)
                    # 确定候选层数，最多往下看 3 层
                    look_back = min(5, num_layers) 
                    
                    # 构造权重：越高的层概率越大，但也允许选低层
                    # 例如：如果有3层，权重可能是 [0.2, 0.3, 0.5]
                    candidate_indices = list(range(num_layers - look_back, num_layers))
                    # 简单的线性权重，层数越高权重越大
                    # weights = [i + 1 for i in range(len(candidate_indices))]
                    # total_w = sum(weights)
                    # probs = [w / total_w for w in weights]
                    
                    # chosen_idx = np.random.choice(candidate_indices, p=probs)
                    chosen_idx = np.random.choice(candidate_indices)
                    target_z = self.height_list[chosen_idx]
                    support_poly = self.height[target_z]

                    if not support_poly.is_empty:
                        # [策略修改 2]: 拒绝采样 (Rejection Sampling) 替代 中心点
                        # 我们希望在多边形内部随机找点，而不是只用中心点。
                        # 这样积木可以放在边缘，增加横向扩展。
                        
                        minx, miny, maxx, maxy = support_poly.bounds
                        found_sample = False
                        
                        # 尝试 N 次在边界框内撒点
                        for _ in range(15):
                            rx = np.random.uniform(minx, maxx)
                            ry = np.random.uniform(miny, maxy)
                            sample_point = Point(rx, ry)
                            
                            # [关键]: 检查点是否在多边形内
                            # buffer(-0.05) 依然是为了保证稳定性，
                            # 确保重心不贴着边缘，而是稍微靠里一点点
                            if support_poly.buffer(-0.05).contains(sample_point):
                                cx, cy = rx, ry
                                cz = target_z + size[2]/2
                                positions = [(cx, cy, cz)]
                                found_sample = True
                                break
                        
                        # 如果随机撒点没找到（比如多边形太细长），
                        # 回退到使用几何中心，并加一点点扰动
                        if not found_sample:
                            centroid = support_poly.centroid
                            cx = np.random.normal(centroid.x, 0.05)
                            cy = np.random.normal(centroid.y, 0.05)
                            cz = target_z + size[2]/2
                            positions = [(cx, cy, cz)]
                    else:
                        # 异常回退
                        positions = [(0, 0, target_z + size[2]/2)]
                
                else:
                    # 如果不是稳定模式（这里的代码实际上不会走到，因为我们强制了 is_stable_mode）
                    x = np.random.uniform(PROJECTION_X[0], PROJECTION_X[1])
                    y = np.random.uniform(PROJECTION_Y[0], PROJECTION_Y[1])
                    positions = [(x, y, 0)] # Dummy z, handled by validator

                # --- 验证逻辑 (保持不变) ---
                for position in positions:
                    new_polygon = self.get_polygon(position, size, rotation)
                    
                    support_z = position[2] - size[2]/2
                    pos_multipoly = None
                    
                    for h_key in self.height_list:
                        if abs(h_key - support_z) < 0.001:
                            pos_multipoly = self.height[h_key]
                            break
                    
                    if pos_multipoly is None: continue

                    # 1. 面积重叠检测
                    intersection = pos_multipoly.intersection(new_polygon)
                    has_area = intersection.area >= INTERSECTION_THRESHOLD
                    
                    # 2. 重心检测
                    center_point = Point(position[0], position[1])
                    # 注意：这里再次检查 contains 是双重保险
                    is_com_supported = pos_multipoly.buffer(0.001).contains(center_point)

                    if has_area and is_com_supported:
                        valid_positions.append(position)
                        valid_counts += 1

        if not valid_positions:
            return []
            
        # 随机打乱返回，避免每次都取第一个最稳的，增加一点随机性
        random.shuffle(valid_positions)
        return valid_positions

class CollisionDetector:
    def __init__(self):
        pass

    def get_block_vertices(self, position, size, rotation):
        """
        Get the 8 vertices of a block given its position, size, and rotation.
        """
        l, w, h = size
        half_l = l / 2
        half_w = w / 2
        half_h = h / 2

        # Create rotation matrix from Euler angles
        rotation_matrix = Euler(rotation, 'XYZ').to_matrix().to_4x4()

        # 8 vertices in local space
        local_vertices = [
            Vector(( half_l,  half_w,  half_h)),
            Vector(( half_l,  half_w, -half_h)),
            Vector(( half_l, -half_w,  half_h)),
            Vector(( half_l, -half_w, -half_h)),
            Vector((-half_l,  half_w,  half_h)),
            Vector((-half_l,  half_w, -half_h)),
            Vector((-half_l, -half_w,  half_h)),
            Vector((-half_l, -half_w, -half_h))
        ]

        # apply rotation and translation to get world coordinates
        world_vertices = []
        for vertex in local_vertices:
            rotated_vertex = rotation_matrix @ vertex

            world_vertex = Vector(position) + rotated_vertex
            world_vertices.append(world_vertex)

        return world_vertices

    def get_block_faces(self, vertices):
        """
        Get the faces of a block given its vertices.
        Each face is represented by a list of vertices.
        """
        faces = [
            [0, 1, 3, 2],
            [4, 5, 7, 6],
            [0, 4, 6, 2],
            [1, 5, 7, 3],
            [0, 1, 5, 4],
            [2, 3, 7, 6]
        ]

        return [[vertices[i] for i in face] for face in faces]

    def separating_axis_theorem(self, vertices1, vertices2):
        """
        Check for collision between two sets of vertices using the Separating Axis Theorem (SAT).
        Returns True if there is a collision, False otherwise.
        """
        # get all possible separating axes
        normals = self.get_all_separating_axes(vertices1, vertices2)

        # check each axis
        for normal in normals:
            min1, max1 = self.project_vertices(vertices1, normal)
            min2, max2 = self.project_vertices(vertices2, normal)

            if max1 <= min2 or max2 <= min1:
                return False
        # If no separating axis found, there is a collision
        return True

    def get_all_separating_axes(self, vertices1, vertices2):
        """
        Get all possible separating axes for two sets of vertices.
        This includes face normals and edge cross products.
        """
        faces1 = self.get_block_faces(vertices1)
        normals1 = [self.get_face_normal(face) for face in faces1]

        faces2 = self.get_block_faces(vertices2)
        normals2 = [self.get_face_normal(face) for face in faces2]

        edge_normals = []
        for i in range(len(faces1)):
            for j in range(len(faces2)):
                edges1 = self.get_face_edges(faces1[i])
                edges2 = self.get_face_edges(faces2[j])

                for edge1 in edges1:
                    for edge2 in edges2:
                        cross = edge1.cross(edge2)
                        if cross.length > 0.001:  # To avoid zero-length normals
                            edge_normals.append(cross.normalized())

        all_normals = normals1 + normals2 + edge_normals

        unique_normals = []
        seen = set()
        for normal in all_normals:
            # Round to avoid floating point precision issues
            key = (round(normal.x, 3), round(normal.y, 3), round(normal.z, 3))
            if key not in seen:
                seen.add(key)
                unique_normals.append(normal)

        return unique_normals

    def get_face_normal(self, face_vertices):
        """
        Calculate the normal vector of a face given its vertices.
        The face is defined by three vertices.
        """
        v0 = face_vertices[0]
        v1 = face_vertices[1]
        v2 = face_vertices[2]

        edge1 = v1 - v0
        edge2 = v2 - v0

        normal = edge1.cross(edge2).normalized()
        return normal

    def get_face_edges(self, face_vertices):
        """
        Get the edges of a face defined by its vertices.
        Each edge is represented as a vector from one vertex to the next.
        """
        edges = []
        n = len(face_vertices)
        for i in range(n):
            j = (i + 1) % n
            edge = face_vertices[j] - face_vertices[i]
            edges.append(edge)
        return edges

    def project_vertices(self, vertices, axis):
        """
        Project the vertices onto a given axis and return the min and max values.
        The axis should be a normalized vector.
        """
        min_val = float('inf')
        max_val = float('-inf')

        for vertex in vertices:
            projection = vertex.dot(axis)

            if projection < min_val:
                min_val = projection
            if projection > max_val:
                max_val = projection

        return min_val, max_val

    def check_block_collision(self, existing_blocks, new_position, new_size, new_rotation):
        """
        Check if a new block collides with existing blocks in the scene.
        """
        new_vertices = self.get_block_vertices(new_position, new_size, new_rotation)

        for block in existing_blocks:

            existing_vertices = self.get_block_vertices(
                block['position'],
                block['size'],
                block['rotation']
            )

            if self.separating_axis_theorem(new_vertices, existing_vertices):
                return True

        return False

class FeatureSampler:
    """
    统一控制以下特征的分布尽量均匀：
      - 深度 D
      - 对称性 S
      - 重心 Gx, Gy, Gz
    通过在 (D,S) 的 2D 网格 和 (Gx,Gy,Gz) 的 3D 网格上做均匀“占坑”。
    """
    def __init__(self,
                 bins_DS=(6, 6),
                 bins_G=(6, 6, 6),
                 lims_D=(0.0, 0.6),
                 lims_S=(0.0, 0.8),
                 lims_Gx=(-1.5, 1.5),
                 lims_Gy=(-0.8, 0.8),
                 lims_Gz=(1.0, 5.0)):
        # 网格尺寸
        self.bins_DS = bins_DS
        self.bins_G = bins_G

        # 范围
        self.lims = {
            "D":  lims_D,
            "S":  lims_S,
            "Gx": lims_Gx,
            "Gy": lims_Gy,
            "Gz": lims_Gz,
        }

        # 计数直方图
        self.hist_DS = np.zeros(bins_DS, dtype=int)   # (D,S) 的 2D 直方图
        self.hist_G  = np.zeros(bins_G,  dtype=int)   # (Gx,Gy,Gz) 的 3D 直方图

        # 记录所有已接受场景的特征
        self.records = []  # 每条记录: (D, S, Gx, Gy, Gz)

    @staticmethod
    def _to_bin(value, vmin, vmax, nbins):
        # 把连续值裁剪到 [vmin, vmax] 并映射到 [0, nbins-1]
        value = max(vmin, min(vmax, value))
        if vmax == vmin:  # 保险
            return 0
        return int((value - vmin) / (vmax - vmin) * (nbins - 1))

    def get_bin_index_DS(self, D, S):
        i = self._to_bin(D, *self.lims["D"],  self.bins_DS[0])
        j = self._to_bin(S, *self.lims["S"],  self.bins_DS[1])
        return (i, j)

    def get_bin_index_G(self, Gx, Gy, Gz):
        a = self._to_bin(Gx, *self.lims["Gx"], self.bins_G[0])
        b = self._to_bin(Gy, *self.lims["Gy"], self.bins_G[1])
        c = self._to_bin(Gz, *self.lims["Gz"], self.bins_G[2])
        return (a, b, c)

    def accept_scene(self, D, S, Gx, Gy, Gz,
                     max_density_DS=4,
                     max_density_G=4):
        """
        判断是否接受该场景：
        - (D,S) 所在的网格格子里，样本数 < max_density_DS
        - (Gx,Gy,Gz) 所在的格子里，样本数 < max_density_G
        两者都没超，就接受。
        """
        idx_DS = self.get_bin_index_DS(D, S)
        idx_G  = self.get_bin_index_G(Gx, Gy, Gz)

        if self.hist_DS[idx_DS] >= max_density_DS:
            return False
        if self.hist_G[idx_G] >= max_density_G:
            return False

        # 占坑并记录
        self.hist_DS[idx_DS] += 1
        self.hist_G[idx_G]   += 1
        self.records.append((float(D), float(S), float(Gx), float(Gy), float(Gz)))
        return True

    def save_distribution(self, dirpath, prefix="feature_distribution"):
        """
        把当前分布信息保存成两个 json：
          - 前缀_DS_G.json：记录 bins / lims / hist / records
          - 方便你之后画图看均匀程度
        """
        os.makedirs(dirpath, exist_ok=True)
        path = os.path.join(dirpath, f"{prefix}.json")
        data = {
            "bins_DS": self.bins_DS,
            "bins_G":  self.bins_G,
            "lims":    self.lims,
            "hist_DS": self.hist_DS.tolist(),
            "hist_G":  self.hist_G.tolist(),
            "records": self.records
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"📊 特征分布已保存到: {path}")

def check_stability_simulation(blocks_data, ped_num, threshold=0.03, frames=60):
    """
    运行快速物理模拟来检测塔是否稳定。
    Args:
        blocks_data: 积木数据
        ped_num: 底部基座积木的数量（通常认为基座是固定的或作为基础）
        threshold: 判定为移动/倒塌的位移阈值（米）
        frames: 模拟帧数（通常60帧/2秒足够判断是否立即倒塌）
    Returns:
        bool: True 表示稳定，False 表示倒塌
    """
    scene = bpy.context.scene

    # 1. 为所有积木添加物理属性 (Active Rigid Body)
    for block in blocks_data:
        obj_name = f"block_{block['index']}"
        obj = bpy.data.objects.get(obj_name)
        if obj:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.rigidbody.object_add()
            obj.rigid_body.type = 'ACTIVE'
            # 使用原脚本定义的摩擦力，或者为了严格稳定测试，稍微降低一点摩擦力
            obj.rigid_body.friction = 0.5
            obj.rigid_body.mass = 1.0
            # 碰撞形状设为 BOX 提高计算速度和精度
            obj.rigid_body.collision_shape = 'BOX'

    # 确保有物理世界
    if scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()

    rw = scene.rigidbody_world
    rw.point_cache.frame_start = 1
    rw.point_cache.frame_end = frames

    # 2. 烘焙物理 (Bake)
    # 先清除旧缓存
    bpy.ops.ptcache.free_bake_all()
    # 烘焙
    try:
        bpy.ops.ptcache.bake_all(bake=True)
    except RuntimeError:
        # 有时没有缓存可烘焙会报错，忽略
        pass

    # 3. 检查位移
    is_stable = True
    scene.frame_set(frames) # 跳转到模拟结束帧

    for block in blocks_data:
        # 跳过基座积木的严格检测（如果基座被设计为不动的话），或者全部检测
        obj_name = f"block_{block['index']}"
        obj = bpy.data.objects.get(obj_name)
        if not obj: continue

        # 计算位移距离
        current_pos = obj.matrix_world.translation
        original_pos = Vector(block['position'])
        displacement = (current_pos - original_pos).length

        # 如果任何一个积木位移超过阈值，视为不稳定
        if displacement > threshold:
            is_stable = False
            # print(f"Block {block['index']} unstable. Disp: {displacement:.3f}")
            break

    # 4. 清理与重置 (非常重要！)
    # 我们需要把场景恢复到初始状态，以便后续渲染生成的视频是从头开始的
    bpy.ops.ptcache.free_bake_all()
    scene.frame_set(1)

    # 移除刚体，防止干扰后续逻辑（后续 physics_render 会重新添加）
    for block in blocks_data:
        obj_name = f"block_{block['index']}"
        obj = bpy.data.objects.get(obj_name)
        if obj:
            # 移除刚体属性
            bpy.context.view_layer.objects.active = obj
            bpy.ops.rigidbody.object_remove()

            # 强制重置位置和旋转（消除模拟产生的微小抖动）
            obj.location = Vector(block['position'])
            obj.rotation_euler = Euler(block['rotation'])

    return is_stable

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)

    for block in bpy.data.materials:
        bpy.data.materials.remove(block)

    for block in bpy.data.images:
        bpy.data.images.remove(block)

    for block in bpy.data.cameras:
        bpy.data.cameras.remove(block)

    for block in bpy.data.lights:
        bpy.data.lights.remove(block)

    for block in bpy.data.actions:
        bpy.data.actions.remove(block)

    bpy.ops.ptcache.free_bake_all()
    if bpy.context.scene.rigidbody_world is not None:
        bpy.ops.rigidbody.world_remove()

    import gc
    gc.collect()

def setup_camera(cam_loc=(0, -20, 2), cam_rot=(1.5, 0, 0)):
    """
        Set up the camera.
        Args:
            cam_loc
            cam_rot
            video_len
            fps
    """
    cam_data = bpy.data.cameras.new('SceneCamera')
    cam_obj = bpy.data.objects.new('SceneCamera', cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.location = cam_loc
    cam_obj.rotation_euler = cam_rot
    bpy.context.scene.camera = cam_obj
    create_camera_animation(cam_obj)

def create_camera_animation(camera, target_loc=(0, 0, 2.5)):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=target_loc)
    empty = bpy.context.object
    empty.name = "CameraTarget"
    camera.parent = empty

    # 计算各阶段帧数
    rot_frames = ROTATION_LEN * FPS
    phys_frames = VIDEO_LEN * FPS
    
    # 关键帧时间点
    # 1. 第一阶段结束点 (旋转结束，准备开始物理)
    t1 = rot_frames
    # 2. 第二阶段结束点 (物理结束，准备开始最后旋转)
    t2 = rot_frames + phys_frames
    # 3. 总时长 (最后旋转结束)
    total_frames = rot_frames + phys_frames + rot_frames
    
    bpy.context.scene.frame_end = total_frames

    # --- 设置关键帧 ---
    
    # 1. 初始状态 (Frame 1): 角度 0
    empty.rotation_euler = (0, 0, 0)
    empty.keyframe_insert(data_path="rotation_euler", frame=1)

    # 2. 第一阶段结束 (Frame t1): 旋转一圈 (360度)
    empty.rotation_euler = (0, 0, math.radians(360))
    empty.keyframe_insert(data_path="rotation_euler", frame=t1)
    
    # 3. 物理阶段保持视角 (Frame t1+1 到 t2): 
    # 为了方便观察物理，通常保持静止，或者重置回正面。
    # 这里我们让它重置回 0 度（正面）静止观察倒塌
    # 如果你希望它接着刚才的 360 度继续转，可以删掉下面这块，但通常静止好观察。
    
    # 在物理开始时，切回 0 度 (或者你喜欢的固定角度)
    empty.rotation_euler = (0, 0, 0) 
    empty.keyframe_insert(data_path="rotation_euler", frame=t1+1)
    
    # 在物理结束时，依然保持 0 度
    empty.rotation_euler = (0, 0, 0)
    empty.keyframe_insert(data_path="rotation_euler", frame=t2)

    # 4. 最后阶段结束 (Frame total): 再转一圈
    empty.rotation_euler = (0, 0, math.radians(360))
    empty.keyframe_insert(data_path="rotation_euler", frame=total_frames)

    # --- 设置线性插值 (让旋转匀速，而不是由慢到快) ---
    if empty.animation_data and empty.animation_data.action:
        for fcurve in empty.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'

def render_two_views(index, config, output_dir="renders", resolution=(800, 800)):
    """
    从分界线前后两个方向拍静态图；临时切换输出为 PNG，渲染后恢复原设置。
    功能更新：
    1. 动态调整相机高度(Z)和距离(Y)以适配塔的高度。
    2. 使用 PNG 格式输出。
    """
    os.makedirs(output_dir, exist_ok=True)
    scene = bpy.context.scene
    num_blocks = config['Scene'].get("num_blocks")

    # —— 保存旧设置（可能是 FFMPEG 等动画格式）——
    prev_engine = scene.render.engine
    prev_resx, prev_resy = scene.render.resolution_x, scene.render.resolution_y
    prev_file_format = scene.render.image_settings.file_format
    prev_filepath = scene.render.filepath
    prev_use_ext = scene.render.use_file_extension
    prev_ffmpeg_format = getattr(scene.render, "ffmpeg", None).format if hasattr(scene.render, "ffmpeg") else None

    try:
        # —— 切到静帧图片设置 ——
        scene.render.engine = 'CYCLES'
        scene.render.resolution_x, scene.render.resolution_y = resolution
        scene.cycles.samples = 128
        scene.render.image_settings.file_format = 'PNG'   # ☆ 关键：避免“动画格式”单帧写入报错
        scene.render.use_file_extension = True

        # 删除旧相机（避免多个相机干扰）
        for obj in list(bpy.data.objects):
            if obj.type == 'CAMERA':
                bpy.data.objects.remove(obj, do_unlink=True)
        
        # === 动态相机位置计算 ===
        # 1. 获取当前塔的最大高度
        tower_height = compute_H()
        if tower_height < 1.0: tower_height = 1.0 # 防止空场景或过矮导致的异常

        # 2. 计算相机 Z 轴 (高度): 居中于塔的垂直中心
        cam_z = tower_height / 2.0

        # 3. 计算相机 Y 轴 (距离): 
        # 为了防止塔太高超出镜头，距离需要随高度增加。
        # 经验值：使用 2.0 倍塔高作为距离通常能覆盖默认镜头的垂直视野。
        # 同时保留原有的 15 作为最小距离。
        cam_dist = max(15.0, tower_height * 2.0)

        # 定义两个视角：沿 x=0 分界线，分别从 -Y (Front) 和 +Y (Back) 看向中心
        # 注意：rotation (90, 0, 0) 是水平向前看，配合 Z=tower_height/2 正好居中拍摄
        camera_positions = [
            {"name": "front", "location": (0, -cam_dist, cam_z), "rotation": (math.radians(90), 0, 0)},
            {"name": "back",  "location": (0,  cam_dist, cam_z), "rotation": (math.radians(90), 0, math.radians(180))},
        ]

        for cam in camera_positions:
            cam_data = bpy.data.cameras.new(f"Cam_{cam['name']}")
            cam_obj = bpy.data.objects.new(f"Cam_{cam['name']}", cam_data)
            scene.collection.objects.link(cam_obj)
            scene.camera = cam_obj

            cam_obj.location = cam["location"]
            cam_obj.rotation_euler = Euler(cam["rotation"], 'XYZ')

            # 设置输出路径（带 .png 后缀更稳）
            img_path = os.path.join(output_dir, f"{DARK_OR_LIGHT}_{num_blocks}_{STABILITY}_{index}_{cam['name']}.png")
            scene.render.filepath = img_path

            # 渲染静帧
            bpy.ops.render.render(write_still=True)
            print(f"✅ 场景 {index} 已保存视角 {cam['name']} 图像：{img_path}")

        # 清理相机
        for obj in list(bpy.data.objects):
            if obj.type == 'CAMERA':
                bpy.data.objects.remove(obj, do_unlink=True)

    finally:
        # —— 恢复原设置 ——
        scene.render.engine = prev_engine
        scene.render.resolution_x, scene.render.resolution_y = prev_resx, prev_resy
        scene.render.image_settings.file_format = prev_file_format
        scene.render.filepath = prev_filepath
        scene.render.use_file_extension = prev_use_ext
        if hasattr(scene.render, "ffmpeg") and prev_ffmpeg_format is not None:
            scene.render.ffmpeg.format = prev_ffmpeg_format

def render_six_views(index, config, output_dir="renders", resolution=(800, 800)):
    """
    生成6个视角的静态图。
    每个视角下，旋转地面，使分界线位于视野正中间（垂直于视线）。
    返回最后一次的相机位置和角度，供视频渲染使用。
    """
    os.makedirs(output_dir, exist_ok=True)
    scene = bpy.context.scene
    
    # 渲染设置
    prev_engine = scene.render.engine
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.cycles.samples = 128
    scene.render.image_settings.file_format = 'PNG'

    # 获取地面对象
    ground = bpy.data.objects.get("GrayGround")
    if not ground:
        ground = create_gray_ground()

    # 计算相机参数
    tower_height = compute_H()
    if tower_height < 1.0: tower_height = 1.0
    cam_z = tower_height / 2.0
    cam_dist = max(15.0, tower_height * 1.9) # 稍微拉远一点保证全景

    # 定义6个角度 (0, 60, 120, 180, 240, 300)
    angles = [i * 60 for i in range(6)]
    
    last_cam_obj = None # 用于保留引用

    for i, deg in enumerate(angles):
        rad = math.radians(deg)
        
        # 1. 计算相机位置 (极坐标转笛卡尔)
        # 角度定义：0度在 -Y 轴 (Front)，逆时针旋转
        # 注意 Blender 中 Front View 通常是 -Y 看向 +Y
        # 这里我们可以自定义：0度时相机在 (0, -dist), 90度在 (dist, 0)
        
        # 为了配合地面旋转逻辑，我们设定：
        # 相机位置：x = R * sin(rad), y = -R * cos(rad) 
        # (当 rad=0, pos=(0, -R), 即 Front view)
        cam_x = cam_dist * math.sin(rad)
        cam_y = -cam_dist * math.cos(rad)
        
        # 2. 设置相机
        # 先清理旧相机
        for obj in list(bpy.data.objects):
            if obj.type == 'CAMERA': bpy.data.objects.remove(obj, do_unlink=True)
            
        cam_data = bpy.data.cameras.new(f"Cam_{deg}")
        cam_obj = bpy.data.objects.new(f"Cam_{deg}", cam_data)
        scene.collection.objects.link(cam_obj)
        scene.camera = cam_obj
        
        cam_obj.location = (cam_x, cam_y, cam_z)
        
        # 相机朝向：看向 (0, 0, cam_z)
        # 简单计算欧拉角：Z轴旋转 = rad, X轴旋转 = 90度
        cam_obj.rotation_euler = Euler((math.radians(90), 0, rad), 'XYZ')
        
        # 3. 旋转地面
        # 地面初始状态：X>0 浅, X<0 深。分界线是 Y 轴。
        # 初始相机(0度)在 -Y 处看向 +Y。此时分界线正好把视野分成左(X<0)右(X>0)。
        # 当相机旋转 rad 度，地面也需要旋转 rad 度，才能保持分界线相对于相机不动。
        if np.random.randint(2) == 1:
            ground.rotation_euler.z = math.radians(deg+180)
        else:
            ground.rotation_euler.z = rad 

        # 4. 渲染
        view_name = f"view{i}"
        img_path = os.path.join(output_dir, f"{DARK_OR_LIGHT}_{config['Scene']['num_blocks']}_{STABILITY}_{index}_{view_name}.png")
        scene.render.filepath = img_path
        bpy.ops.render.render(write_still=True)
        print(f"📸 Saved View {i} ({deg}°): {img_path}")
        
        last_cam_obj = cam_obj

    # 循环结束后，场景保留在最后一个视角的状态
    # 恢复渲染引擎设置 (可选，如果后续视频渲染需要特定设置)
    return (cam_x, cam_y, cam_z)

def setup_light(light_type='POINT'):
    """
    Set up point lights and the background light.
    """
    loc_list = []
    r = 8
    num_lights = 12
    angle_step = 2 * math.pi / num_lights
    for j in range(num_lights):
        angle = j * angle_step
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        loc_list.append((x, y, 2.5))
    num_lights_2 = 6
    angle_step_2 = 2 * math.pi / num_lights_2
    r2 = 5.5
    for j in range(num_lights_2):
        angle = j * angle_step_2
        x = r2 * math.cos(angle)
        y = r2 * math.sin(angle)
        loc_list.append((x, y, 5))

    for i, loc in enumerate(loc_list):
        light_data = bpy.data.lights.new(name=f'SceneLight_{i}', type=light_type)
        light_data.energy = 300
        light_data.color = (1, 1, 1)
        light_obj = bpy.data.objects.new(name=f'SceneLight_{i}', object_data=light_data)
        bpy.context.collection.objects.link(light_obj)
        light_obj.location = loc

    bpy.context.scene.world.use_nodes = True
    env = bpy.context.scene.world.node_tree.nodes['Background']
    env.inputs['Color'].default_value = (0, 0, 0, 1)

def create_material(obj, color, mat_name):
    """
    Set up block's material.
    Args:
        obj: a blender object (block)
        color: string
        mat_name: string
    """
    whole_name = mat_name + color
    mat_params = MATERIALS.get(mat_name)
    mat = bpy.data.materials.new(name=whole_name)
    mat.use_nodes = True

    mat.node_tree.nodes.clear()

    bsdf = mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    for key, value in mat_params.items():
        bsdf.inputs[key].default_value = value
    bsdf.inputs[0].default_value = COLORS[color]

    output = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    mat.node_tree.links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])

    mat.node_tree.update_tag()
    bpy.context.view_layer.update()

    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    #obj.visible_shadow = False
    obj.visible_diffuse = False
    obj.visible_glossy = False
    obj.visible_transmission = False

    cycles_obj = obj.cycles
    cycles_obj.is_shadow_catcher = False
    #cycles_obj.case_shadow = False
    cycles_obj.diffuse_bounce = 0
    cycles_obj.glossy_bounce = 0
    cycles_obj.transmission_bounce = 0
    cycles_obj.transparent_bounce = 0

    obj.data.update_tag()
    bpy.context.view_layer.update()

def create_gray_ground():
    """
    Create ground. Add material and physics. Set up render settings.
    """
    bpy.ops.mesh.primitive_circle_add(vertices=100, radius=20, fill_type='TRIFAN', location=(0, 0, 0))
    ground = bpy.context.object
    ground.name = "GrayGround"
    mesh = ground.data

    vcol_layer = mesh.vertex_colors.new(name="Col")
    for poly in mesh.polygons[:len(mesh.polygons)//2]:
        for i in poly.loop_indices:
            vcol_layer.data[i].color = COLORS['dark_gray']
    for poly in mesh.polygons[len(mesh.polygons)//2:]:
        for i in poly.loop_indices:
            vcol_layer.data[i].color = COLORS['light_gray']

    mat = bpy.data.materials.new(name="GroundMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    vcol_node = nodes.new(type='ShaderNodeVertexColor')
    vcol_node.layer_name = "Col"

    output = nodes.new(type='ShaderNodeOutputMaterial')
    links.new(vcol_node.outputs['Color'], output.inputs['Surface'])

    ground.visible_diffuse = False
    ground.visible_glossy = False
    ground.visible_transmission = False

    cycles_obj = ground.cycles
    cycles_obj.is_shadow_catcher = False
    cycles_obj.diffuse_bounce = 0
    cycles_obj.glossy_bounce = 0
    cycles_obj.transmission_bounce = 0
    cycles_obj.transparent_bounce = 0

    ground.data.materials.append(mat)
    bpy.ops.object.shade_smooth()

    bpy.context.view_layer.objects.active = ground
    bpy.ops.rigidbody.object_add()
    ground.rigid_body.type = 'PASSIVE'

    return ground

def create_block_mesh(size):
    """
    Create a block mesh based on the size.
    Args:
        size: lenth, width and height
    """
    size_str = f"{size[0]:.1f}X{size[1]:.1f}X{size[2]:.1f}"
    mesh_name = f"BlockMesh_{size_str}"

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)

    scale_matrix = Matrix((
    (size[0], 0, 0, 0),
    (0, size[1], 0, 0),
    (0, 0, size[2], 0),
    (0, 0, 0, 1)
    ))
    bmesh.ops.transform(bm, matrix=scale_matrix, verts=bm.verts)

    mesh = bpy.data.meshes.new(mesh_name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh

def generate_a_block(block_data):
    """
    Generate a block based on block_data. Add material and physics.
    """
    index = block_data['index']
    color = block_data['color']
    mat_name = block_data['material']
    size = block_data['size']
    pos = block_data['position']
    rot = block_data['rotation']
    mesh = create_block_mesh(size)

    try:
        obj = bpy.data.objects.new(f"block_{index}", mesh)
        obj.location = Vector(pos)
        obj.rotation_euler = Euler(rot)
        create_material(obj, color, mat_name)
        bpy.context.scene.collection.objects.link(obj)
        return True
    except Exception as e:
        return False

    #set_block_physics(obj)

def create_mesh(mesh_type, block_data=None):
    """
    Create object mesh. 
    Args:
        mesh_type: 'PLANE' or 'BLOCK'
        block_data: if 'BLOCK'
    """
    if mesh_type == 'PLANE':
        create_gray_ground()
        return True
    elif mesh_type == 'BLOCK':
        return generate_a_block(block_data)

def setup_render(resolution_x=800, resolution_y=800, samples=128):
    """
    Set up basic render settings.
    Args:
        index: scene index
        resolution_x
        resolution_y
        samples
    """
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.render.resolution_x = resolution_x
    bpy.context.scene.render.resolution_y = resolution_y
    bpy.context.scene.cycles.samples = samples

    cycles = bpy.context.scene.cycles
    cycles.device = 'GPU'
    cycles.max_bounces = 0
    cycles.diffuse_bounces = 0
    cycles.glossy_bounces = 0
    cycles.transmission_bounces = 0
    cycles.transparent_max_bounces = 0

    cycles.caustics_reflective = False
    cycles.caustics_refractive = False
    cycles.use_transparent_shadows = False

    # bpy.context.scene.frame_start = 1
    # bpy.context.scene.frame_end = VIDEO_LEN * FPS

    bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
    bpy.context.scene.render.ffmpeg.format = 'MPEG4'

    bpy.context.scene.render.fps = FPS

def get_block_position(existing_blocks, heightmap, collisiondetector, new_size, new_rot, gray_tone, flag=0):
    """
    Generate a block's position.
    Args:
        existing_blocks: dic
        heightmap
        collisiondetector
        size: size of the current block
        new_rot: rotation of the current block
        gray_tone: 'dark_gray' -> negative
        flag: if it's pedestal then flag equals to 1
    """
    valid_positions = heightmap.get_valid_positions(new_size, new_rot, flag, gray_tone)
    if not valid_positions:
        return None
        raise ValueError("No valid positions available for the block.")
    while valid_positions:
        if np.random.uniform(0.0, 1.0) < FATNESS:
            position = valid_positions[0]
        else:
            position = random.choice(valid_positions)
        valid_positions.remove(position)
        if not collisiondetector.check_block_collision(existing_blocks, position, new_size, new_rot):
            heightmap.update_heightmap(position, new_size, new_rot)
            return position
    return None
    raise ValueError("No valid position found for the block after checking all options.")

def generate_blocks_data(config, heightmap, collisiondetector, gray_tone):
    """
    Generate blocks data.
    Args:
        config: dictionary from yaml
        heightmap
        collisiondetector
        red_or_green: string 'red' or 'green'. If red, more x are negative.
    """
    blocks_data = []
    num_blocks = config['Scene']['num_blocks']#29
    ori_color_dic = config['Scene']['num_colors']#{"yellow": 13, "blue": 14, "white": 2}#7,9,1
    color_dic = {}
    for key, value in ori_color_dic.items():
        color_dic[key] = value
    ori_size_dic = config['Scene']['sizes']#{(0.5, 0.5, 1.5): 16, (1.5, 0.5, 0.5): 13}#8,9
    size_dic = {}
    for key, value in ori_size_dic.items():
        key_t = ast.literal_eval(key)
        size_dic[key_t] = value
    if ROT_DISCRETE == False:
        rot_range = config['Scene']['rot_range']#[0, 360]
        assert len(rot_range) == 2
        rot_range = [math.radians(rot_range[0]), math.radians(rot_range[1])]
    else:
        rot_range = config['Scene']['rot_range']#[0, 90, 180, 270]
        rot_range = [math.radians(rot_range[i]) for i in range(len(rot_range))]
    mat = config['Scene']['material']#'wood'

    ped_num = random.randint(2, 5)
    for i in range(num_blocks):
        if i < ped_num:
            if ROT_DISCRETE == False:
                new_rotation = (0, 0, random.uniform(rot_range[0], rot_range[1]))
            else:
                new_rotation = (0, 0, random.choice(rot_range))
            new_position = get_block_position(blocks_data, heightmap, collisiondetector, (0.5, 0.5, 1.5), new_rotation, gray_tone, 1)
            if new_position is None:
                return None, None, False
            block_data = {
                'index' : i,
                'color' : random.choice([key for key in color_dic.keys() if color_dic[key] > 0]),
                'material' : mat,
                'size' : (0.5, 0.5, 1.5),
                'position' : new_position,
                'rotation' : new_rotation
            }
        else:
            if i % 2 == 1 and size_dic[(0.5, 0.5, 1.5)] > 0:
                new_size = (0.5, 0.5, 1.5)
            else:
                new_size = (1.5, 0.5, 0.5)
            if ROT_DISCRETE == False:
                new_rotation = (0, 0, random.uniform(rot_range[0], rot_range[1]))
            else:
                new_rotation = (0, 0, random.choice(rot_range))
            new_position = get_block_position(blocks_data, heightmap, collisiondetector, new_size, new_rotation, gray_tone)
            block_data = {
                'index' : i,
                'color' : random.choice([key for key in color_dic.keys() if color_dic[key] > 0]),
                'material' : mat,
                'size' : new_size,
                'position' : new_position,
                'rotation' : new_rotation
            }
        color_dic[block_data['color']]-=1
        size_dic[block_data['size']]-=1
        blocks_data.append(block_data)
    return blocks_data, ped_num, True

def set_block_physics(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.object_add()
    obj.rigid_body.type = 'ACTIVE'

def no_physics_render(index, config_num_colors):
    #num_blocks = config_num_colors['yellow'] + config_num_colors['blue'] + config_num_colors['white']
    #for i in range(num_blocks):
    #obj = bpy.data.objects[f'block_{i}']
    #obj.rigid_body.type = 'PASSIVE'
    bpy.context.scene.render.filepath = OUTPUT_PATH + f"/{index}_{config_num_colors['yellow']}_{config_num_colors['blue']}_{config_num_colors['white']}.mp4"
    bpy.ops.render.render(animation=True, write_still=True)

def physics_render(index, ped_num, config):
    """
    Bake and render with distinct phases: Pre-Rotation -> Physics -> Post-Rotation.
    """
    if bpy.context.scene.rigidbody_world is None:
        raise ValueError("No rigidbody_world!")

    num_blocks = config['Scene']['num_blocks']
    
    # 添加刚体
    for i in range(num_blocks):
        obj = bpy.data.objects.get(f'block_{i}')
        if obj:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.rigidbody.object_add()
            obj.rigid_body.type = 'ACTIVE'

    # --- 计算时间轴 ---
    rot_frames = ROTATION_LEN * FPS
    phys_frames = VIDEO_LEN * FPS
    total_frames = rot_frames + phys_frames

    rigidbody_world = bpy.context.scene.rigidbody_world
    
    # [关键修改]: 设置物理模拟的起止帧
    # 物理只在中间阶段运行。在 start 之前，物体会被 Blender 视为静止。
    rigidbody_world.point_cache.frame_start = rot_frames + 1
    rigidbody_world.point_cache.frame_end = rot_frames + phys_frames

    # 烘焙物理
    # 注意：烘焙时最好清除旧的
    bpy.ops.ptcache.free_bake_all()
    bpy.ops.ptcache.bake_all(bake=True)

    # --- 获取倒塌结果用于判断颜色 ---
    # 我们需要在物理阶段结束的那一帧去检查位置
    check_frame = rot_frames + phys_frames
    
    positions = []
    for i in range(num_blocks):
        obj = bpy.data.objects.get(f'block_{i}')
        if obj:
            bpy.context.scene.frame_set(check_frame) # 跳转到物理结束帧
            loc = obj.matrix_world.to_translation()
            positions.append(loc)
            
    if STABILITY == "unstable":
        tilt_color = get_final_tilt_color(positions, DARK_OR_LIGHT, ped_num)
    else:
        tilt_color = "stable"
    
    # 设置渲染输出路径
    bpy.context.scene.render.filepath = OUTPUT_PATH + f"/videos/{DARK_OR_LIGHT}_{num_blocks}_{STABILITY}_{index}_{tilt_color}.mp4"

    # --- 渲染设置 ---
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = total_frames # 渲染所有三个阶段
    
    # 开始渲染
    bpy.ops.render.render(animation=True, write_still=True)
    
    # 渲染后清理物理缓存，防止影响下一个场景
    bpy.ops.ptcache.free_bake_all()
    
    return tilt_color

def physics_render_last_view(index, config):
    """
    只渲染当前视角的物理倒塌视频 (即第6个视角)。
    """
    scene = bpy.context.scene
    num_blocks = config['Scene']['num_blocks']
    
    # 视频设置
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.fps = FPS
    
    # 物理烘焙
    if scene.rigidbody_world:
        # 稳定的塔不需要预旋转阶段，或者缩短预旋转
        # 这里假设直接开始物理
        total_frames = VIDEO_LEN * FPS
        scene.rigidbody_world.point_cache.frame_start = 1
        scene.rigidbody_world.point_cache.frame_end = total_frames
        scene.frame_end = total_frames
        
        bpy.ops.ptcache.free_bake_all()
        bpy.ops.ptcache.bake_all(bake=True)
        
    # 输出路径
    vid_path = os.path.join(OUTPUT_PATH, "videos", f"{DARK_OR_LIGHT}_{num_blocks}_{STABILITY}_{index}_{STABILITY}.mp4")
    scene.render.filepath = vid_path
    
    bpy.ops.render.render(animation=True, write_still=True)
    print(f"🎬 Video Saved: {vid_path}")
    
    bpy.ops.ptcache.free_bake_all()

def get_final_tilt_color(block_positions, gray_tone, ped_num):
    """
    Args:
        block_positions: list, positions for all blocks after physics simulation
    """
    count = 0
    for p in block_positions:
        if gray_tone == 'light_gray':
            if p[0] >= 0:
                count += 1
        else:
            if p[0] <= 0:
                count += 1
    if count >= len(block_positions) // 2:
        return gray_tone
    else:
        print("reverse")
        if gray_tone == 'light_gray':
            return 'dark_gray'
        else:
            return 'light_gray'

def load_scene_config(yml_path='configs/config.yml'):
    """
    Load config and set up global variables.
    """
    with open(yml_path, 'r') as f:
        config = yaml.safe_load(f)

    global SEED, INTERSECTION_THRESHOLD, FATNESS, NUM_SCENES, DARK_OR_LIGHT, STABILITY, VIDEO_LEN, FPS
    global ROTATION_LEN
    global DEGREE, POINT
    global PROJECTION_X, PROJECTION_Y
    global ROT_DISCRETE
    global OUTPUT_PATH

    SEED = config['General'].get("SEED", 42)
    INTERSECTION_THRESHOLD = config['General'].get("INTERSECTION_THRESHOLD",
                                                   0.01)
    FATNESS = config['General'].get("FATNESS", 0.5)

    NUM_SCENES = config['General'].get("NUM_SCENES", 1)
    DARK_OR_LIGHT = config['General'].get("DARK_OR_LIGHT")
    STABILITY = config['General'].get("STABILITY")

    VIDEO_LEN = config['General'].get("VIDEO_LEN", 6)
    ROTATION_LEN = config['General'].get("ROTATION_LEN", 3)
    FPS = config['General'].get("FPS", 30)

    DEGREE = config['General'].get("DEGREE", 10)
    POINT = config['General'].get("POINT", None)

    PROJECTION_X = config['General'].get("PROJECTION_X", [-1.5, 2.5])
    PROJECTION_Y = config['General'].get("PROJECTION_Y",
                                         [-1.5, 1.5])  #(-0.75, 0.75)

    ROT_DISCRETE = config['General'].get("ROT_DISCRETE", False)

    OUTPUT_PATH = config['General'].get("OUTPUT_PATH")

    random.seed(SEED)
    np.random.seed(SEED)
    return config

# —— 工具：从对象获取世界空间的 8 顶点（复用之前的 CollisionDetector 逻辑）——
def get_block_vertices_world(obj):
    """
    返回该 Blender 对象方块在世界坐标系下的 8 顶点（Vector 列表）
    要求 obj 是你脚本中按尺寸生成的正方体/长方体“block_i”。
    """
    # 从对象拿到世界矩阵，将其局部包围盒点变换到世界
    # 为与脚本一致，这里用基于尺寸与旋转的精确顶点生成：
    size = obj.dimensions  # 世界尺寸（含缩放）
    # 由于 dimensions 受旋转影响较复杂，采用碰撞器的做法：从中心与欧拉角构造
    # 直接读脚本里的数据更稳：obj.location, obj.rotation_euler, 和“设计尺寸”
    # 这里假设对象的“实际盒尺寸”为 obj.bound_box 计算更安全：
    world_mat = obj.matrix_world
    verts = [world_mat @ Vector(corner) for corner in obj.bound_box]  # 8 个角
    return verts

def convex_hull_polygon_xy(points):
    """给一组三维点，投影到 x–y 平面，返回 shapely 的凸包多边形。"""
    pts2d = [(p.x, p.y) for p in points]
    try:
        poly = Polygon(pts2d).convex_hull
    except Exception:
        poly = Polygon(pts2d)
    return poly

def convex_hull_polygon_xz(points):
    """给一组三维点，投影到 x–z 平面，返回 shapely 的凸包多边形。"""
    pts2d = [(p.x, p.z) for p in points]
    try:
        poly = Polygon(pts2d).convex_hull
    except Exception:
        poly = Polygon(pts2d)
    return poly

def block_center_world(obj):
    """方块世界几何中心（用对象世界矩阵作用于局部原点）。"""
    return (obj.matrix_world @ Vector((0,0,0)))

def block_top_bottom_z(obj):
    """返回该方块顶面/底面高度 (z_top, z_bot) —— 从 8 顶点得出。"""
    verts = get_block_vertices_world(obj)
    z_vals = [v.z for v in verts]
    return (max(z_vals), min(z_vals))

def list_blocks_in_scene():
    """列出所有按脚本命名的方块对象。"""
    return [obj for obj in bpy.data.objects if obj.name.startswith("block_")]  #

# —— 1) N ——
def compute_N():
    return len(list_blocks_in_scene())

# —— 2) H ——
def compute_H():
    H = 0.0
    for obj in list_blocks_in_scene():
        verts = get_block_vertices_world(obj)
        H = max(H, max(v.z for v in verts))
    return float(H)

# —— 3) D（遮挡平均比例，沿 y 轴正交投影到 x–z）——
def compute_D_front():
    blocks = list_blocks_in_scene()
    if not blocks:
        return 0.0
    # 为定义前后顺序：按中心 y 升序（小的在前，先遮挡后面的）
    sorted_blocks = sorted(blocks, key=lambda o: block_center_world(o).y)
    # 预先算每个块在 x–z 的投影与面积
    proj_polys = {}
    areas = {}
    for obj in sorted_blocks:
        poly = convex_hull_polygon_xz(get_block_vertices_world(obj))
        proj_polys[obj.name] = poly
        areas[obj.name] = max(poly.area, 1e-9)  # 防止除零

    # 逐块累积“前方”并集，计算被遮挡面积
    front_union = None
    occluded_ratios = []
    for obj in sorted_blocks:
        poly = proj_polys[obj.name]
        if front_union is None:
            occluded_area = 0.0
            front_union = poly
        else:
            inter = poly.intersection(front_union)
            occluded_area = inter.area if not inter.is_empty else 0.0
            front_union = unary_union([front_union, poly])
        occluded_ratios.append(occluded_area / areas[obj.name])

    return float(np.mean(occluded_ratios))

def compute_D_back():
    blocks = list_blocks_in_scene()
    if not blocks:
        return 0.0
    # 为定义前后顺序：按中心 y 升序（小的在前，先遮挡后面的）
    sorted_blocks = sorted(blocks, key=lambda o: block_center_world(o).y, reverse=True)
    # 预先算每个块在 x–z 的投影与面积
    proj_polys = {}
    areas = {}
    for obj in sorted_blocks:
        poly = convex_hull_polygon_xz(get_block_vertices_world(obj))
        proj_polys[obj.name] = poly
        areas[obj.name] = max(poly.area, 1e-9)  # 防止除零

    # 逐块累积“前方”并集，计算被遮挡面积
    front_union = None
    occluded_ratios = []
    for obj in sorted_blocks:
        poly = proj_polys[obj.name]
        if front_union is None:
            occluded_area = 0.0
            front_union = poly
        else:
            inter = poly.intersection(front_union)
            occluded_area = inter.area if not inter.is_empty else 0.0
            front_union = unary_union([front_union, poly])
        occluded_ratios.append(occluded_area / areas[obj.name])

    return float(np.mean(occluded_ratios))

# —— 4) G（所有方块中心的平均）——
def compute_G():
    blocks = list_blocks_in_scene()
    if not blocks:
        return (0.0, 0.0, 0.0)
    centers = [block_center_world(o) for o in blocks]
    x = sum(c.x for c in centers)/len(centers)
    y = sum(c.y for c in centers)/len(centers)
    z = sum(c.z for c in centers)/len(centers)
    return (float(x), float(y), float(z))

# —— 层解析：支撑面高度集合（按顶面 z）——
def compute_layer_tops(eps=1e-4):
    blocks = list_blocks_in_scene()
    tops = []
    for o in blocks:
        z_top, _ = block_top_bottom_z(o)
        tops.append(z_top)
    tops.sort()
    # 合并接近的层
    merged = []
    for z in tops:
        if not merged or abs(z - merged[-1]) > eps:
            merged.append(z)
    return merged  # 由低到高

# —— 构建“某层支撑平台”的 x–y 平面形状（由该层所有顶面的投影并集得到）——
def support_polygon_xy_for_layer(layer_z, eps=1e-4):
    polys = []
    for o in list_blocks_in_scene():
        z_top, _ = block_top_bottom_z(o)
        if abs(z_top - layer_z) <= eps:
            # 取该块顶面的四个顶点（z 接近 z_top 的顶点）
            verts = get_block_vertices_world(o)
            top_verts = [v for v in verts if abs(v.z - z_top) <= 1e-3]
            if len(top_verts) >= 3:
                polys.append(convex_hull_polygon_xy(top_verts))
    if not polys:
        return None
    return unary_union(polys)

# —— 5) LG：每层以上的子塔重心（序列，与层顺序对应）——
def compute_LG():
    layers = compute_layer_tops()
    LG = []
    blocks = list_blocks_in_scene()
    for h in layers:
        # 子塔 = 底面 >= 该层高度 的所有块
        selected = []
        for o in blocks:
            _, z_bot = block_top_bottom_z(o)
            if z_bot >= h - 1e-4:  # 兼容浮点
                selected.append(block_center_world(o))
        if selected:
            cx = sum(p.x for p in selected)/len(selected)
            cy = sum(p.y for p in selected)/len(selected)
            cz = sum(p.z for p in selected)/len(selected)
            LG.append((float(cx), float(cy), float(cz)))
        else:
            LG.append((None, None, None))
    return LG

# —— 6) S：对称性（按 x 轴，取各层平台左右外伸差的一半乘层高，再取最大）——
def compute_S():
    H_global = compute_H()
    layers = compute_layer_tops()
    best = 0.0
    for h in layers:
        poly = support_polygon_xy_for_layer(h)
        if poly is None or poly.is_empty:
            continue
        # 用外接框近似左右最远点（也可用边界坐标直接求）
        minx, miny, maxx, maxy = poly.bounds
        cx, cy = poly.centroid.x, poly.centroid.y
        x_left  = cx - minx
        x_right = maxx - cx
        sym_a = abs(x_left - x_right)/2.0 * h
        best = max(best, sym_a)
    return float(best)

# —— 7) P：每层“顶层块”的几何中心到该层支撑平台几何中心的平均距离（序列）——
def compute_P():
    layers = compute_layer_tops()
    P = []
    blocks = list_blocks_in_scene()
    for h in layers:
        poly = support_polygon_xy_for_layer(h)
        if poly is None or poly.is_empty:
            P.append(None)
            continue
        c = poly.centroid
        # 找到该层的“顶层块”（顶面高度≈h）
        dists = []
        for o in blocks:
            z_top, _ = block_top_bottom_z(o)
            if abs(z_top - h) <= 1e-4:
                ctr = block_center_world(o)
                # 投影到支撑面（x–y 即可），与平台几何中心距离
                d = math.hypot(ctr.x - c.x, ctr.y - c.y)
                dists.append(d)
        if dists:
            P.append(float(np.mean(dists)))
        else:
            P.append(None)
    return P

# —— 总入口：返回所有指标 ——
def compute_tower_metrics():
    return {
        "N": compute_N(),
        "H": compute_H(),
        "D_front": compute_D_front(),
        "D_back": compute_D_back(),
        "G": compute_G(),
        "LG": compute_LG(),
        "S": compute_S(),
        "P": compute_P(),
    }

def save_scene_metrics_to_json(index, features, output_dir, extra_info=None):
    """
    将当前场景的指标保存到一个 JSON 文件中。
    Args:
        index (int): 场景编号
        features (dict): compute_tower_metrics() 的返回值
        output_dir (str): 保存路径文件夹
        extra_info (dict): 可选附加信息，如 {'tilt_color': 'red'}
    """
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "tower_features.json")

    # 如果文件已存在，读取旧内容
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    # 组装一条新的记录
    record = {
        "scene_name": f"{DARK_OR_LIGHT}_{features['N']}_{STABILITY}_{index}",
        "features": features,
    }
    if extra_info:
        record.update(extra_info)

    # 添加进数据列表
    data.append(record)

    # 写回文件
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"场景 {index} 的属性已保存到 {json_path}")

def save_block_data_to_json(index, blocks_data, num_blocks, output_dir="metrics"):
    """
    将当前场景的每个方块信息保存为 JSON 文件。
    Args:
        index (int): 场景编号
        blocks_data (list[dict]): generate_blocks_data() 返回的方块列表
        output_dir (str): 输出文件夹
    """
    import os, json
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"{DARK_OR_LIGHT}_{num_blocks}_{STABILITY}_{index}.json")

    # 将所有 block 信息整理成纯数据结构
    blocks_list = []
    for block in blocks_data:
        block_info = {
            "index": block["index"],
            "name": f"block_{block['index']}",
            "position": list(map(float, block["position"])),
            "rotation_euler": list(map(float, block["rotation"])),
            "size": list(map(float, block["size"])),
            "color": block["color"],
            "material": block["material"]
        }
        blocks_list.append(block_info)

    # 写入文件
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(blocks_list, f, indent=4, ensure_ascii=False)

    print(f"场景 {index} 的方块信息已保存到 {json_path}")


def main():
    # 尝试从命令行参数获取 config 路径 (在 "--" 之后)
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        config_path = args[0]
    else:
        # 如果没有传入参数（比如你在Blender界面里直接点运行），使用默认路径测试
        # 请确保这个路径是你存在的某个文件，用于调试
        config_path = r'F:\YXP\PhD\BlockTower\TowerTask\configs\config.yml'

    print(f"========================================")
    print(f"正在加载配置文件: {config_path}")
    print(f"========================================")

    config = load_scene_config(config_path)
    num_blocks = config['Scene'].get("num_blocks")
    config_num_colors = {}
    for key, value in config['Scene']['num_colors'].items():
        config_num_colors[key] = value

    # 统一特征采样器：D, S, Gx, Gy, Gz
    sampler = FeatureSampler(
        bins_DS=(6, 6),  # D × S 分 6×6 格
        bins_G=(4, 4, 4),  # Gx × Gy × Gz 分 6×6×6 格
        lims_D=(0.0, 0.6),
        lims_S=(0.0, 0.8),
        lims_Gx=(-1.5, 1.5),
        lims_Gy=(-0.8, 0.8),
        lims_Gz=(1.0, 5.0))

    accepted = 0  # 已经“保留”的场景数（你真正要用的刺激数量）
    attempt = 0  # 总的尝试次数（包括被丢弃的）

    # for i in range(NUM_SCENES):
    while accepted < NUM_SCENES:
        if os.path.exists(f"{OUTPUT_PATH}/rawdata/{DARK_OR_LIGHT}_{num_blocks}_{STABILITY}_{accepted}.json"):
            accepted += 1
            continue
        
        if attempt >= 3000:
            print(f"❌ 无法采样到足够数量的场景 (已接受 {accepted}/{NUM_SCENES})")
            break
        
        print(
            f"\n======== 生成尝试 {attempt} (已接受 {accepted}/{NUM_SCENES}) ========"
        )

        clear_scene()

        heightmap = Heightmap()
        collisiondetector = CollisionDetector()
        blocks_data = []
        blocks_data, ped_num, is_success = generate_blocks_data(
            config, heightmap, collisiondetector, DARK_OR_LIGHT)

        if not is_success:
            print(f"❌ 丢弃场景 (尝试 {attempt})：没有符合特征分布的摆放方法")
            attempt += 1
            if attempt >= 3000:
                print(f"❌ 无法采样到足够数量的场景 (已接受 {accepted}/{NUM_SCENES})")
                break
            continue  # 重新生成一个新场景

        setup_render()

        create_mesh('PLANE')

        for block_data in blocks_data:
            block_creation = create_mesh('BLOCK', block_data)
            if not block_creation:
                break
        
        if not block_creation:
            print(f"❌ 丢弃场景 (尝试 {attempt})：无法生成新的物块")
            attempt += 1
            if attempt >= 3000:
                print(f"❌ 无法采样到足够数量的场景 (已接受 {accepted}/{NUM_SCENES})")
                break
            continue

        setup_camera()
        setup_light()

        # 如果塔在物理引擎中倒塌，直接丢弃，不进行特征计算
        # 阈值设为 0.05 (5cm)，稍微的晃动允许，掉落不允许
        if STABILITY == "stable":
            if not check_stability_simulation(
                    blocks_data, ped_num, threshold=0.05, frames=40):
                print(f"⚠️ 丢弃场景 (尝试 {attempt})：积木塔不稳定")
                attempt += 1
                if attempt >= 3000:
                    print(f"❌ 无法采样到足够数量的场景 (已接受 {accepted}/{NUM_SCENES})")
                    break

                continue  # 重新开始循环
        else:
            if check_stability_simulation(blocks_data,
                                          ped_num,
                                          threshold=0.05,
                                          frames=40):
                print(f"⚠️ 丢弃场景 (尝试 {attempt})：积木塔不倒")
                attempt += 1
                if attempt >= 3000:
                    print(f"❌ 无法采样到足够数量的场景 (已接受 {accepted}/{NUM_SCENES})")
                    break
                continue  # 重新开始循环

        feature_set = compute_tower_metrics()
        D = (float(feature_set["D_front"]) + float(feature_set["D_back"])) / 2
        S = float(feature_set["S"])
        Gx, Gy, Gz = feature_set["G"]

        # 用采样器判断是否接受该场景
        if not sampler.accept_scene(
                D, S, Gx, Gy, Gz, max_density_DS=4, max_density_G=3):
            print(
                f"⚠️ 丢弃场景 (尝试 {attempt})：D={D:.3f}, S={S:.3f}, G=({Gx:.3f}, {Gy:.3f}, {Gz:.3f})"
            )
            attempt += 1
            if attempt >= 3000:
                print(f"❌ 无法采样到足够数量的场景 (已接受 {accepted}/{NUM_SCENES})")
                break

            continue  # 重新生成一个新场景

        # ✅ 真正“保留”的场景 —— 用连续编号 accepted
        print(
            f"✅ 接受场景 {accepted}：D={D:.3f}, S={S:.3f}, G=({Gx:.3f}, {Gy:.3f}, {Gz:.3f})"
        )

        # no_physics_render(i, config_num_colors)
        cam_pos = render_six_views(accepted, config, output_dir=f"{OUTPUT_PATH}/images")
        setup_camera(cam_loc=(0, -20, cam_pos[2]))
        physics_render_last_view(accepted, config)
        print(f"Finish creating scene {accepted}.")

        extra = {"tilt_color": None, "stability": STABILITY}
        save_scene_metrics_to_json(accepted,
                                   feature_set,
                                   output_dir=OUTPUT_PATH,
                                   extra_info=extra)

        save_block_data_to_json(accepted, blocks_data, num_blocks=config['Scene'].get("num_blocks"), output_dir=f"{OUTPUT_PATH}/rawdata")

        accepted += 1
        attempt += 1

        if attempt >= 3000:
            print(f"❌ 无法采样到足够数量的场景 (已接受 {accepted}/{NUM_SCENES})")
            break

    sampler.save_distribution(OUTPUT_PATH, prefix="feature_distribution")
    if accepted == NUM_SCENES:
        print("🎯 所有场景生成完毕，并已尽量均匀覆盖 D, S, Gx, Gy, Gz 特征空间。")
    else:
        print("⚠️ 目前生成的场景已保存。")

if __name__=="__main__":
    main()
