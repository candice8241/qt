#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Powder Module - 终极修复版本
使用 multiprocessing 完全隔离集成进程
"""

from PyQt6.QtCore import QTimer
import subprocess
import sys
import os

class IntegrationRunner:
    """使用子进程运行集成，完全隔离"""
    
    @staticmethod  
    def run_in_subprocess(poni_path, mask_path, input_pattern, output_dir, 
                         dataset_path, npt, unit, formats, 
                         create_stacked_plot, stacked_plot_offset):
        """
        在独立的子进程中运行集成
        这样即使集成卡住，也不会影响主GUI
        """
        
        # 创建Python脚本
        script = f'''
import sys
sys.path.insert(0, "{os.path.dirname(os.path.abspath(__file__))}")

from batch_integration import run_batch_integration

try:
    run_batch_integration(
        poni_file="{poni_path}",
        mask_file="{mask_path}" if "{mask_path}" else None,
        input_pattern="{input_pattern}",
        output_dir="{output_dir}",
        dataset_path="{dataset_path}" if "{dataset_path}" else None,
        npt={npt},
        unit="{unit}",
        formats={formats},
        create_stacked_plot={create_stacked_plot},
        stacked_plot_offset="{stacked_plot_offset}",
        disable_progress_bar=True
    )
    print("\\n\\n=== INTEGRATION SUCCESS ===")
except Exception as e:
    print(f"\\n\\n=== INTEGRATION ERROR: {{e}} ===")
    import traceback
    traceback.print_exc()
'''
        
        # 写入临时脚本
        script_path = os.path.join(output_dir, '_integration_worker.py')
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)
        
        # 在子进程中运行
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return process

# 在 powder_module.py 中使用此方法的代码示例：
'''
def run_integration_subprocess(self):
    """使用子进程运行集成 - 不会卡住GUI"""
    try:
        # 参数验证...
        
        self.log("="*60)
        self.log("Starting Integration in subprocess...")
        self.progress.start()
        
        # 收集参数
        formats = []
        if self.format_xy: formats.append('xy')
        if self.format_dat: formats.append('dat')
        if self.format_chi: formats.append('chi')
        if self.format_fxye: formats.append('fxye')
        if self.format_svg: formats.append('svg')
        if self.format_png: formats.append('png')
        if not formats: formats = ['xy']
        
        unit_map = {
            '2θ (°)': '2th_deg',
            'q (nm⁻¹)': 'q_nm^-1',
            'q (A⁻¹)': 'q_A^-1',
            'r (mm)': 'r_mm'
        }
        unit_pyFAI = unit_map.get(self.unit, '2th_deg')
        
        # 启动子进程
        process = IntegrationRunner.run_in_subprocess(
            self.poni_path,
            self.mask_path if self.mask_path else "",
            self.input_pattern,
            self.output_dir,
            self.dataset_path if self.dataset_path else "",
            self.npt,
            unit_pyFAI,
            formats,
            self.create_stacked_plot,
            self.stacked_plot_offset
        )
        
        # 使用定时器检查进程状态
        self.integration_process = process
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_process_status)
        self.check_timer.start(500)  # 每500ms检查一次
        
        self.log("✓ Integration subprocess started")
        
    except Exception as e:
        self.progress.stop()
        self.log(f"❌ Error: {str(e)}")
        self.show_error("Error", str(e))

def _check_process_status(self):
    """检查子进程状态"""
    if hasattr(self, 'integration_process'):
        retcode = self.integration_process.poll()
        
        if retcode is not None:
            # 进程已结束
            self.check_timer.stop()
            self.progress.stop()
            
            stdout, stderr = self.integration_process.communicate()
            
            if "INTEGRATION SUCCESS" in stdout:
                self.log("✓ Integration completed!")
                self.log("="*60)
                self.show_success("Success", "Integration completed successfully!")
            else:
                self.log(f"❌ Integration failed")
                if stderr:
                    self.log(f"Error output: {stderr}")
                self.log("="*60)
                self.show_error("Error", "Integration failed. Check log for details.")
'''
