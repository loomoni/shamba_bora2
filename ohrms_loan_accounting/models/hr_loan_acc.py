# -*- coding: utf-8 -*-
import time
from odoo import models, api
from odoo.exceptions import UserError
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HrLoanAcc(models.Model):
    _inherit = 'hr.loan'

    @api.multi
    def action_approve(self):
        """This create account move for request.
            """
        loan_approve = self.env['ir.config_parameter'].sudo().get_param('account.loan_approve')
        contract_obj = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)])
        if not contract_obj:
            raise UserError('You must Define a contract for employee')
        if not self.loan_lines:
            raise UserError('You must compute installment before Approved')
        if loan_approve:
            self.write({'state': 'waiting_approval_2'})
        else:
            if not self.emp_account_id or not self.treasury_account_id or not self.journal_id:
                raise UserError("You must enter employee account & Treasury account and journal to approve ")
            if not self.loan_lines:
                raise UserError('You must compute Loan Request before Approved')
            timenow = time.strftime('%Y-%m-%d')
            for loan in self:
                amount = loan.loan_amount
                loan_name = loan.employee_id.name
                reference = loan.name
                journal_id = loan.journal_id.id
                debit_account_id = loan.treasury_account_id.id
                credit_account_id = loan.emp_account_id.id
                debit_vals = {
                    'name': loan_name,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'loan_id': loan.id,
                    'partner_id': loan.employee_id.user_id.partner_id.id,
                }
                credit_vals = {
                    'name': loan_name,
                    'account_id': credit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'loan_id': loan.id,
                    'partner_id': loan.employee_id.user_id.partner_id.id,
                }
                vals = {
                    'name': 'Loan For' + ' ' + loan_name,
                    'narration': loan_name,
                    'ref': reference,
                    'journal_id': journal_id,
                    'date': timenow,
                    'partner_id': loan.employee_id.user_id.partner_id.id,
                    'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
                }
                move = self.env['account.move'].create(vals)
                move.post()
            self.write({'state': 'approve'})
        return True

    @api.multi
    def action_double_approve(self):
        """This create account move for request in case of double approval.
            """
        if self.partner_bank_account_id and not self.partner_bank_account_id.currency_id:
            raise ValidationError(_("Please Call HR to Enter Payee Bank Account Currency"))
        if not self.treasury_account_id:
            raise ValidationError(_("Please Select The Credit Account (Where the loan funds are coming from eg Bank A/C)"))
        if not self.emp_account_id:
            raise ValidationError(_("Please Select The Debit Account (Where the loan funds are going to eg Cash A/C)"))
        if not self.journal_id:
            raise ValidationError(_("Please Select The Payment Journal"))
        if not self.to_journal_id:
            raise ValidationError(_("Please Select The Debit Journal"))
        if not self.emp_account_id or not self.treasury_account_id or not self.journal_id:
            raise UserError("You must enter employee account & Treasury account and journal to approve ")
        if not self.loan_lines:
            raise UserError('You must compute Loan Request before Approved')
        timenow = time.strftime('%Y-%m-%d')
        for loan in self:
            # amount = loan.loan_amount
            # loan_name = loan.employee_id.name
            # reference = loan.name
            # journal_id = loan.journal_id.id
            # debit_account_id = loan.treasury_account_id.id
            # credit_account_id = loan.emp_account_id.id
            # debit_vals = {
            #     'name': loan_name,
            #     'account_id': debit_account_id,
            #     'journal_id': journal_id,
            #     'date': timenow,
            #     'debit': amount > 0.0 and amount or 0.0,
            #     'credit': amount < 0.0 and -amount or 0.0,
            #     'loan_id': loan.id,
            #
            #     'partner_id': loan.employee_id.user_id.partner_id.id,
            # }
            # credit_vals = {
            #     'name': loan_name,
            #     'account_id': credit_account_id,
            #     'journal_id': journal_id,
            #     'date': timenow,
            #     'debit': amount < 0.0 and -amount or 0.0,
            #     'credit': amount > 0.0 and amount or 0.0,
            #     'loan_id': loan.id,
            #     'partner_id': loan.employee_id.user_id.partner_id.id,
            # }
            # vals = {
            #     'name': 'Loan For' + ' ' + loan_name,
            #     'narration': loan_name,
            #     'ref': reference,
            #     'journal_id': journal_id,
            #     'date': timenow,
            #     'partner_id': loan.employee_id.user_id.partner_id.id,
            #     'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            # }
            # move = self.env['account.move'].create(vals)
            # move.post()
            loanrequestAmount = loan.loan_amount
            if loan.partner_bank_account_id:
                if loan.company_id.currency_id != loan.partner_bank_account_id.currency_id:
                    if loan.partner_bank_account_id.currency_id.rate <= 0:
                        rate = 1
                    else:
                        rate = loan.partner_bank_account_id.currency_id.rate
                    loanrequestAmount = loan.loan_amount * rate
            payment_methods = loan.journal_id.inbound_payment_method_ids or loan.journal_id.outbound_payment_method_ids
            payment_method_id = payment_methods and payment_methods[0] or False
            if loan.partner_bank_account_id:
                payment_id = self.env['account.payment'].sudo().create({
                    'loan_id': loan.id,
                    'staff_payment': True,
                    'staff_payment_to_account_id': loan.treasury_account_id.id,
                    'payment_type': 'outbound',
                    'payment_date': fields.date.today(),
                    'journal_id': loan.journal_id.id,
                    'destination_journal_id': loan.to_journal_id.id,
                    'payment_method_id': payment_method_id.id,
                    'partner_id': loan.employee_id.user_id.partner_id.id,
                    'partner_type': 'supplier',
                    'currency_id': loan.partner_bank_account_id.currency_id.id,
                    'amount': loanrequestAmount,
                    'communication': loan.name,
                    'name': loan.name,
                    'partner_bank_id': loan.partner_bank_account_id.id,
                    'is_payroll': True
                })
            else:
                payment_id = self.env['account.payment'].sudo().create({
                    'loan_id': loan.id,
                    'staff_payment': True,
                    'staff_payment_to_account_id': loan.treasury_account_id.id,
                    'payment_type': 'outbound',
                    'payment_date': fields.date.today(),
                    'journal_id': loan.journal_id.id,
                    'destination_journal_id': loan.to_journal_id.id,
                    'payment_method_id': payment_method_id.id,
                    'partner_id': loan.employee_id.user_id.partner_id.id,
                    'partner_type': 'supplier',
                    'currency_id': loan.currency_id.id,
                    'amount': loanrequestAmount,
                    'communication': loan.name,
                    'name': loan.name,
                    'is_payroll': True
                })
            if payment_id:
                payment_id.post()
                loan.write({'payment_line_id': payment_id.id})
        self.write({'state': 'approve'})
        return True


class HrLoanLineAcc(models.Model):
    _inherit = "hr.loan.line"

    @api.one
    def action_paid_amount(self):
        """This create the account move line for payment of each installment.
            """
        timenow = time.strftime('%Y-%m-%d')
        for line in self:
            if line.loan_id.state != 'approve':
                raise UserError("Loan Request must be approved")
            amount = line.amount
            loan_name = line.employee_id.name
            reference = line.loan_id.name
            journal_id = line.loan_id.journal_id.id
            debit_account_id = line.loan_id.emp_account_id.id
            credit_account_id = line.loan_id.treasury_account_id.id
            debit_vals = {
                'name': loan_name,
                'account_id': debit_account_id,
                'journal_id': journal_id,
                'date': timenow,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'partner_id': line.loan_id.employee_id.user_id.partner_id.id,
            }
            credit_vals = {
                'name': loan_name,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'date': timenow,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'partner_id': line.loan_id.employee_id.user_id.partner_id.id,
            }
            vals = {
                'name': 'Loan For' + ' ' + loan_name,
                'narration': loan_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': timenow,
                'partner_id': line.loan_id.employee_id.user_id.partner_id.id,
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move = self.env['account.move'].create(vals)
            move.post()
        return True


class HrPayslipAcc(models.Model):
    _inherit = 'hr.payslip'

    @api.multi
    def action_payslip_done(self):
        for line in self.input_line_ids:
            if line.loan_line_id:
                line.loan_line_id.action_paid_amount()
        return super(HrPayslipAcc, self).action_payslip_done()

class AccountPaymentLoan(models.Model):
    _inherit = 'account.payment'

    loan_id = fields.Many2one('hr.loan', string='Loan')