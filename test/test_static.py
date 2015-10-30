import rw.static


def test_hash_file_adblock():
    """for the first two bytes are 4096 different possibilities of which 4 match
       "ad".  Checking against 50k makes it extremly unlikely we have
       no "ad" starting hash

       The current implementation hits for example:
        178 = AdVFedpEauHnXNqAjNGIQ4g0-mJJsVEmnbD5Ejyd3GE
        286 = ADKM5Xu8FLM71mlbyOsyzfL7Xzp9iewUpCgl4V0532A
        616 = aD0JggWxFVDy1xAWyCxDd6lsn4COEy-D8VupvQWMeyA
    """

    for i in range(50000):
        h = rw.static.file_hash(str(i).encode('utf-8'))
        h = h[:2].lower()
        assert h != 'ad', i
