# -*- coding: utf-8 -*-
from gt4py.cartesian import gtscript

from cloudsc4py.physics._stencils.fcttre import f_foeeice, f_foeeliq
from ifs_physics_common.framework.stencil import function_collection
from ifs_physics_common.utils.f2py import ported_function


@ported_function(from_file="common/include/fccld.func.h", from_line=26, to_line=27)
@function_collection("f_fokoop")
@gtscript.function
def f_fokoop(t):
    from __externals__ import RKOOP1, RKOOP2

    return min(RKOOP1 - RKOOP2 * t, f_foeeliq(t) / f_foeeice(t))