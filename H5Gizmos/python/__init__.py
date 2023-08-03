
# hack numpy
import numpy as np
if not hasattr(np, "float"):
    np.float = float
