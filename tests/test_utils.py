from py3dtiles.utils import make_aabb_valid


def test_make_aabb_valid() -> None:
    aabb = [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]
    make_aabb_valid(aabb)
    assert aabb == [[0, 0, 0], [1, 1, 1]]
    aabb = [[0, 0, 0], [0, 0, 0]]
    make_aabb_valid(aabb)
    assert aabb == [[0, 0, 0], [0.00001, 0.00001, 0.00001]]
    aabb = [[9, 10, 11], [9, 10, 11]]
    make_aabb_valid(aabb)
    assert aabb == [[9, 10, 11], [9.00001, 10.00001, 11.00001]]
    aabb = [[9, 12, 14], [10, 13, 15]]
    make_aabb_valid(aabb)
    assert aabb == [[9, 12, 14], [10, 13, 15]]
    aabb = [[9, 12, 14], [9, 13, 15]]
    make_aabb_valid(aabb)
    assert aabb == [[9, 12, 14], [9.00001, 13, 15]]
