import unittest
import numpy as np
from portable import make_tokens,inputs
from score import rows_to_people,one_table

class TestMethods(unittest.TestCase):
    def test_measured_samples_and_masks(self):
        g=np.arange(60).reshape(1,20,3);a=100+g
        raw=make_tokens(g,a,np.arange(20)[None]/100,['left'],[9])
        np.testing.assert_array_equal(raw[0,-1,:3],g[0,-1])
        np.testing.assert_array_equal(raw[0,-1,3:6],g[0,-4:].mean(0))
        np.testing.assert_array_equal(raw[0,-1,6:9],a[0,-1])
        self.assertAlmostEqual(raw[0,-1,12],.2)
        v=inputs(raw,dict(x_mean=np.zeros(33),x_scale=np.ones(33),mode='gyro_task'))
        self.assertTrue((v[:,:,6:12]==0).all());self.assertEqual(v[0,0,15+8],1)
    def test_original_before_person(self):
        # Person 1 has two originals with different numbers of eligible windows.
        values=np.array([[0],[0],[6],[2]],float)
        people,result=rows_to_people(values,np.array([1,1,1,2]),np.array(['left']*4),np.array([1,1,2,3]))
        np.testing.assert_array_equal(people,[1,2]);np.testing.assert_array_equal(result,[[3],[2]])
    def test_paired_block(self):
        s={'participant':np.array([1,1,1,2]),'hand':np.array(['left']*4),'trial':np.array([1,1,2,3])}
        vals=np.array([[0.,0.,6.,2.]])
        l={'gyro':{'transformer_full':vals,'transformer_gyro_task':vals+2,'transformer_wrong_accel':vals+1}}
        table=one_table(l,s,np.ones(4,bool),'gyro')
        self.assertEqual(table['scores']['transformer_full']['error'],2.5)
        np.testing.assert_allclose(table['full_minus']['transformer_gyro_task']['interval'],[-2,-2])
    def test_input_shape(self):
        with self.assertRaises(ValueError):make_tokens(np.zeros((1,21,3)),np.zeros((1,20,3)),np.arange(20)[None]/100,['right'],[2])
if __name__=='__main__':unittest.main()
