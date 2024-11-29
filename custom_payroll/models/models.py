# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from io import BytesIO
import base64
from datetime import *
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell
from dateutil.relativedelta import relativedelta
from odoo.addons import decimal_precision as dp

class HrPayslipEmployeesInherited(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    @api.multi
    def compute_sheet(self):
        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end', 'credit_note'])
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not data['employee_ids']:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': active_id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': run_data.get('credit_note'),
                'company_id': employee.company_id.id,
            }
            payslips += self.env['hr.payslip'].create(res)
        payslips.compute_sheet()
        payslipRun = self.env['hr.payslip.run'].search([('id','=',active_id)], limit=1)
        if payslipRun:
            payslipRun.write({'state':'generated'})
        return {'type': 'ir.actions.act_window_close'}

class HrPayslipRunCustomInherited(models.Model):
    _name = 'hr.payslip.run'
    _inherit = ['hr.payslip.run', 'mail.thread', 'mail.activity.mixin']

    branch_id = fields.Many2one('hr.branches', string='Branch', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Payslips Generated'),
        ('hr_confirmed', 'Checked by HR'),
        ('bm_confirmed', 'Endorsed By BM'),
        ('confirmed', 'Approved by FM'),
        ('close', 'Closed'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',track_visibility="onchange",)
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payslips',states={'draft': [('readonly', False)], 'generated': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', 'Bank', states={'draft': [('readonly', False)]}, required=True, domain="[('type','in',['bank'])]", default=lambda self: self.env['account.journal'].search([('type', '=', 'bank')], limit=1))

    @api.multi
    def hr_checked_payslip_run(self):
        if self.branch_id.hr_manager_id.user_id.id == self.env.uid:
            self.write({'state': 'hr_confirmed'})
        return True


    @api.multi
    def bm_checked_payslip_run(self):
        if self.branch_id.manager_id.user_id.id == self.env.uid:
            self.write({'state': 'bm_confirmed'})
        return True

    @api.multi
    def confirm_payslip_run(self):
        checkPayslip = False
        for payslip in self.slip_ids:
            if self.env['hr.payslip'].search(
                    [('employee_id', '=', payslip.employee_id.id), ('state', '=', 'done'), ('date_to', '>', payslip.date_from)]):
                checkPayslip = True
                break
        if not checkPayslip:
            for payslip in self.slip_ids:
                if payslip.state != 'cancel':
                    payslip.action_payslip_done()
            self.write({'state': 'confirmed'})
        else:
            raise ValidationError(_('The already exists a payslip for the specified period for selected employees.'))

        return True


class HrPayslipCustomInherited(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'mail.thread', 'mail.activity.mixin']

    is_computed = fields.Boolean(string="Is Computed", default=False)
    payment_id = fields.Many2one('account.payment', string='Payment Line', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Payslip Generated'),
        ('hr_confirmed', 'Checked by HR'),
        ('bm_confirmed', 'Checked by BM'),
        ('done', 'Approved by FM'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft', track_visibility="onchange",
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Payslip Generated\'.
                \n* If the payslip is under hr checking, the status is \'PChecked by HR\'.
                \n* If the payslip is confirmed then status is set to \'Approved\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")

    @api.onchange('line_ids','line_ids.amount')
    def onchange_line_ids(self):
        total = 0
        for line in self.line_ids:
            if line.code.lower() != 'net' and line.code.lower() != 'gross':
                total += line.amount
        for line in self.line_ids:
            if line.code.lower() == 'net':
                line.amount = total

    @api.multi
    def button_reset_sheet(self):
        self.write({'is_computed': False})
        return True

    @api.multi
    def button_acc_confirm(self):
        self.write({'state': 'verify'})
        return True

    @api.multi
    def button_hr_confirm(self):
        if self.employee_id.department_id.branch_id.hr_manager_id.user_id.id == self.env.uid:
            self.write({'state': 'hr_confirmed'})
        return True

    @api.multi
    def button_bm_confirm(self):
        if self.employee_id.department_id.branch_id.manager_id.user_id.id == self.env.uid:
            self.write({'state': 'bm_confirmed'})
        return True

    @api.multi
    def button_recompute_net(self):
        total = 0
        for line in self.line_ids:
            codeValue = line.code.lower()
            if line.code.lower() != 'net' and line.code.lower() != 'gross':
                total += line.amount
        for line in self.line_ids:
            if line.code.lower() == 'net':
                line.amount = total
        return True


    @api.multi
    def compute_sheet(self):
        for payslip in self:
            if payslip.contract_id.journal_id:
                number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
                # delete old payslip lines
                payslip.line_ids.unlink()
                # set the list of contract for which the rules have to be applied
                # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
                contract_ids = payslip.contract_id.ids or \
                    self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
                lines = []
                for line in self._get_payslip_lines(contract_ids, payslip.id):
                    if line['code'] == 'LO':
                        amount = 0
                        for item in payslip.input_line_ids:
                            if item.code == 'LO':
                                amount += item.amount
                        line['amount'] = amount * -1
                        lines.append((0, 0, line))
                    else:
                        lines.append((0, 0, line))
                payslip.write({'line_ids': lines, 'number': number, 'is_computed': True, 'journal_id': payslip.contract_id.journal_id.id})
                payslip.button_recompute_net()
            else:
                raise ValidationError(_('Please Confirm Employee Contract Details For '+ str(payslip.employee_id.name)))
        return True


    @api.multi
    def action_payslip_done(self):
        for item in self:
            if item.employee_id:
                if not item.employee_id.bank_account_id or not item.employee_id.bank_account_id.currency_id:
                    raise ValidationError(
                        _('Please Confirm Employee Bank Details For ' + str(item.employee_id.name)))
        checkPayslip = False
        if self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),('state','=','done'), ('date_to', '>', self.date_from)]):
            checkPayslip = True
        if not checkPayslip:
            for slip in self:
                line_ids = []
                debit_sum = 0.0
                credit_sum = 0.0
                date = slip.date or slip.date_to
                currency = slip.company_id.currency_id

                name = _('Payslip of %s') % (slip.employee_id.name)
                move_dict = {
                    'narration': name,
                    'ref': slip.number,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                }

                salaryDeposit = 0.0
                for line in slip.details_by_salary_rule_category:
                    amount = currency.round(slip.credit_note and -line.total or line.total)
                    if currency.is_zero(amount):
                        continue
                    debit_account_id = line.salary_rule_id.account_debit.id
                    credit_account_id = line.salary_rule_id.account_credit.id
                    if line.salary_rule_id.code.lower() == "net":
                        salaryDeposit = amount

                    if line.salary_rule_id.code.lower() == "lo" and slip.employee_id.user_id:
                        partnerDets = slip.employee_id.user_id.partner_id.id
                    elif line.salary_rule_id.code.lower() == "net" and slip.employee_id.user_id:
                        partnerDets = slip.employee_id.user_id.partner_id.id
                    elif line.salary_rule_id.code.upper() == "STAFF_RECOVERIES" and slip.employee_id.user_id:
                        partnerDets = slip.employee_id.user_id.partner_id.id
                    else:
                        if debit_account_id:
                            partnerDets = line._get_partner_id(credit_account=False)
                        else:
                            partnerDets = line._get_partner_id(credit_account=True)

                    if debit_account_id:
                        debit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': partnerDets,
                            'account_id': debit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount > 0.0 and amount or 0.0,
                            'credit': amount < 0.0 and -amount or 0.0,
                            'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                    if credit_account_id:
                        credit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': partnerDets,
                            'account_id': credit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount < 0.0 and -amount or 0.0,
                            'credit': amount > 0.0 and amount or 0.0,
                            'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                if currency.compare_amounts(credit_sum, debit_sum) == -1:
                    acc_id = slip.journal_id.default_credit_account_id.id
                    if not acc_id:
                        raise UserError(
                            _('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                                slip.journal_id.name))
                    adjust_credit = (0, 0, {
                        'name': _('Adjustment Entry'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': 0.0,
                        'credit': currency.round(debit_sum - credit_sum),
                    })
                    line_ids.append(adjust_credit)

                elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                    acc_id = slip.journal_id.default_debit_account_id.id
                    if not acc_id:
                        raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                            slip.journal_id.name))
                    adjust_debit = (0, 0, {
                        'name': _('Adjustment Entry'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': currency.round(credit_sum - debit_sum),
                        'credit': 0.0,
                    })
                    line_ids.append(adjust_debit)
                move_dict['line_ids'] = line_ids
                payment_methods = slip.journal_id.inbound_payment_method_ids or slip.journal_id.outbound_payment_method_ids
                payment_method_id = payment_methods and payment_methods[0] or False
                if slip.company_id.currency_id != slip.employee_id.bank_account_id.currency_id:
                    if slip.employee_id.bank_account_id.currency_id.rate <= 0:
                        rate = 1
                    else:
                        rate = slip.employee_id.bank_account_id.currency_id.rate
                    salaryDeposit = salaryDeposit * rate
                payment_id = self.env['account.payment'].sudo().create({
                    'payment_type': 'outbound',
                    'name': slip.number,
                    'payment_date': fields.date.today(),
                    'journal_id': slip.journal_id.id,
                    'payment_method_id': payment_method_id.id,
                    'partner_id': slip.employee_id.user_id.partner_id.id,
                    'partner_type': 'supplier',
                    'currency_id': slip.employee_id.bank_account_id.currency_id.id,
                    'amount': salaryDeposit,
                    'communication': "Salary Payment For " + str(slip.employee_id.user_id.partner_id.name),
                    'partner_bank_id': slip.employee_id.bank_account_id.id,
                    'is_payroll': True
                })
                move = self.env['account.move'].create(move_dict)
                slip.write(
                    {'move_id': move.id, 'date': date, 'state': 'done', 'payment_id': payment_id.id, 'paid': True})
                for line in slip.input_line_ids:
                    if line.loan_line_id:
                        if line.amount >= line.loan_line_id.amount:
                            line.loan_line_id.paid = True
                            line.loan_line_id.amount = line.amount
                move.post()
        else:
            raise ValidationError(_('The already exists a payslip for the specified period for ' + str(self.employee_id.name)))

        return True



class PayrollSummary(models.Model):
    _name = 'payroll.summary'
    _description = "Payroll Summary"

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Rule', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True, index=True)
    rate = fields.Float(string='Rate (%)', digits=dp.get_precision('Payroll Rate'), default=100.0)
    amount = fields.Float(digits=dp.get_precision('Payroll'))
    quantity = fields.Float(digits=dp.get_precision('Payroll'), default=1.0)
    total = fields.Float(compute='_compute_total', string='Total', digits=dp.get_precision('Payroll'), store=True)

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100


class PayrollSummaryWizard(models.TransientModel):
    _name = 'payroll.summary.wizard'

    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    company = fields.Many2one('res.company', default=lambda self: self.env['res.company']._company_default_get(),
                              string="Company")


    # to get salary rules names
    @api.multi
    def get_rules(self):
        vals = []

        heads = self.env['hr.salary.rule'].search([('active', 'in', (True, False))], order='sequence asc')
        list = []
        for head in heads:
            list = [head.name, head.code]
            vals.append(list)

        return vals

    @api.multi
    def get_report(self):
        file_name = _('payroll summary '+str(self.date_from)+ ' - '+str(self.date_to)+' report.xlsx')
        fp = BytesIO()

        workbook = xlsxwriter.Workbook(fp)
        heading_format = workbook.add_format({'align': 'center',
                                              'valign': 'vcenter',
                                              'bold': True, 'size': 14})
        cell_text_format_n = workbook.add_format({'align': 'center',
                                                  'bold': True, 'size': 9,
                                                  })
        cell_text_format = workbook.add_format({'align': 'left',
                                                'bold': True, 'size': 9,
                                                })

        cell_text_format.set_border()
        cell_text_format_new = workbook.add_format({'align': 'left',
                                                    'size': 9,
                                                    })
        cell_text_format_new.set_border()
        cell_number_format = workbook.add_format({'align': 'right',
                                                  'bold': False, 'size': 9,
                                                  'num_format': '#,###0.00'})
        cell_number_format.set_border()
        worksheet = workbook.add_worksheet('payroll summary '+str(self.date_from)+ ' - '+str(self.date_to)+' report.xlsx')
        normal_num_bold = workbook.add_format({'bold': True, 'num_format': '#,###0.00', 'size': 9, })
        normal_num_bold.set_border()
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 20)
        worksheet.set_column('E:E', 20)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 20)
        worksheet.set_column('H:H', 20)
        worksheet.set_column('I:I', 20)
        worksheet.set_column('J:J', 20)
        worksheet.set_column('K:K', 20)
        worksheet.set_column('L:L', 20)
        worksheet.set_column('M:M', 20)
        worksheet.set_column('N:N', 20)

        res = self.get_rules()
        row = 2
        row_set = row

        if self.date_from and self.date_to:

            date_2 = datetime.strftime(self.date_to, '%d-%m-%Y')
            date_1 = datetime.strftime(self.date_from, '%d-%m-%Y')
            payroll_month = self.date_from.strftime("%B")
            worksheet.merge_range('A1:F2', 'Payroll For %s %s' % (payroll_month, self.date_from.year),
                                  heading_format)
            worksheet.merge_range('B4:D4', '%s' % (self.company.name), cell_text_format_n)
            column = 0
            worksheet.write(row + 1, 0, 'Company', cell_text_format_n)
            worksheet.write(row, 4, 'Date From', cell_text_format_n)
            worksheet.write(row, 5, date_1 or '')
            row += 1
            worksheet.write(row, 4, 'Date To', cell_text_format_n)
            worksheet.write(row, 5, date_2 or '')
            row += 2

            worksheet.write(row, 0, 'Employee', cell_text_format)
            worksheet.write(row, 1, 'Employee ID', cell_text_format)

            column = 2
            # to write salary rules names in the row
            for vals in res:
                worksheet.write(row, column, vals[0], cell_text_format)
                column += 1
            row += 1
            col = 0
            ro = row

           # payslipResult = self.sudo().compute_employee_payslips(self.date_from,self.date_to)

            payslip_ids = self.env['hr.payslip'].sudo().search(
                [('date_from', '=', self.date_from), ('date_to', '=', self.date_to), ('state', '=', 'done')])
            if payslip_ids:

                for payslip in payslip_ids:
                    name = payslip.employee_id.name
                    id = payslip.employee_id.identification_id

                    worksheet.write(ro, col, name or '', cell_text_format_new)
                    worksheet.write(ro, col + 1, id or '', cell_text_format_new)

                    ro = ro + 1
            col = col + 2
            colm = col

            if payslip_ids:
                for payslip in payslip_ids:
                    for vals in res:
                        r = 0
                        check = False
                        for line in payslip.line_ids:
                            if line.code == vals[1]:
                                check = True
                                r = line.total

                        if check == True:

                            worksheet.write(row, col, r, cell_number_format)


                        else:
                            worksheet.write(row, col, 0, cell_number_format)

                        col += 1
                    row += 1
                    col = colm
        worksheet.write(row, 0, 'Grand Total', cell_text_format)
        # calculating sum of columnn
        roww = row
        columnn = 2
        for vals in res:
            cell1 = xl_rowcol_to_cell(row_set + 1, columnn)

            cell2 = xl_rowcol_to_cell(row - 1, columnn)
            worksheet.write_formula(row, columnn, '{=SUM(%s:%s)}' % (cell1, cell2), normal_num_bold)
            columnn = columnn + 1

        worksheet.write(row, 1, '', cell_text_format)
        worksheet.write(row, 2, '', cell_text_format)

        workbook.close()
        file_download = base64.b64encode(fp.getvalue())
        fp.close()

        self = self.with_context(default_name=file_name, default_file_download=file_download)

        return {
            'name': 'Payroll Summary Report Download',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'payroll.summary.excel',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }

    @api.multi
    def compute_employee_payslips(self,date_from,date_to):
        employees = []
        for employee in self.env['hr.employee'].search([('active','=',True)]):
            if self.env['hr.contract'].search([('employee_id','=',employee.id),('state','=','open')]):
                employees.append(employee)

        for emp in employees:
            checkPayslip = self.env['hr.payslip'].search([('employee_id','=',emp.id),('date_from', '=',date_from), ('date_to', '=', date_to), ('state', '=', 'done')])
            if not checkPayslip:
                slip_data = self.env['hr.payslip'].onchange_employee_id(date_from, date_to, emp.id,
                                                                        contract_id=False)
                res = {
                    'employee_id': emp.id,
                    'name': slip_data['value'].get('name'),
                    'struct_id': slip_data['value'].get('struct_id'),
                    'contract_id': slip_data['value'].get('contract_id'),
                    'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                    'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                    'date_from': date_from,
                    'date_to': date_to,
                    'credit_note': False,
                    'company_id': emp.company_id.id,
                }
                createPayslip = self.env['hr.payslip'].create(res)
                createPayslip.compute_sheet()
                createPayslip.action_payslip_done()

        return True


class PayrollReportExcel(models.TransientModel):
    _name = 'payroll.summary.excel'

    name = fields.Char('File Name', size=256, readonly=True)
    file_download = fields.Binary('Download Payroll', readonly=True)