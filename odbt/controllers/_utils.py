import math

class Utils:
    def eng_string(x, sig_figs=2, si=True, suffix=None):
        """
        Returns float/int value <x> formatted in a simplified engineering format -
        using an exponent that is a multiple of 3.

        sig_figs: number of significant figures

        si: if true, use SI suffix for exponent, e.g. k instead of e3, n instead of
        e-9 etc.
        """
        x = float(x)
        sign = ''
        if x < 0:
            x = -x
            sign = '-'
        if x == 0:
            exp = 0
            exp3 = 0
            x3 = 0
        else:
            exp = int(math.floor(math.log10(x)))
            exp3 = exp - (exp % 3)
            x3 = x / (10 ** exp3)
            x3 = round(x3, -int(math.floor(math.log10(x3)) - (sig_figs - 1)))
            if x3 == int(x3):  # prevent from displaying .0
                x3 = int(x3)

        if si and exp3 >= -24 and exp3 <= 24 and exp3 != 0:
            exp3_text = 'yzafpnum kMGTPEZY'[exp3 // 3 + 8]
        elif exp3 == 0:
            exp3_text = ''
        else:
            exp3_text = 'e%s' % exp3

        return ('%s%s%s%s') % (sign, x3, exp3_text, suffix)